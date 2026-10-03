# Chapter 1 · The world it enters: a client wired to a function, not a socket

> **Enters as:** `app=<function app>`, `transport=httpx.WSGITransport(app=app)`, `base_url='http://testserver'`, every other knob left at its default

The string `"/"` and the dict `{"X-Custom": "value"}` do not exist yet. They are three lines further down the script, waiting to be handed to `client.get()`. Before they can go anywhere, a road has to be built for them — and the notable thing about this road is that it ends at a Python function rather than at a socket.

It begins with the transport. `httpx.WSGITransport(app=app)` does nothing clever: it stores the callable and four defaults on itself and returns — `raise_app_exceptions=True`, `script_name=""`, `remote_addr="127.0.0.1"`, `wsgi_errors=None` ([wsgi.py#L77-L89](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L77-L89)). No connection pool, no SSL context, no DNS. Everything that will later be called "sending a request" is, from this object's point of view, calling `app(environ, start_response)`.

Then `httpx.Client(transport=transport, base_url="http://testserver")`. The constructor hands almost all of its work to `BaseClient.__init__` ([_client.py#L662-L674](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L662-L674)), which is where the configuration that will shape our request gets fixed in place.

The base URL is parsed first. `URL("http://testserver")` runs the full RFC 3986 pipeline — scheme lowercased, host quoted and validated, port normalised (`normalize_port('', 'http')` → `None`), path validated and normalised — and comes back as `ParseResult(scheme='http', userinfo='', host='testserver', port=None, path='', query=None, fragment=None)`. Then `_enforce_trailing_slash` asks for `url.raw_path`, gets `b'/'` because an empty path reads as `/`, sees that it already ends in a slash, and returns the URL untouched ([_client.py#L234-L237](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L234-L237)). That trailing slash matters later: it is the invariant that makes relative-URL merging append rather than overwrite.

The headers setter is the next character, and it is opinionated. Whatever you pass, it first builds four defaults and then layers your headers on top ([_client.py#L305-L316](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L305-L316)):

```
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1
```

Here `headers=None`, so `Headers.update(Headers({}))` finds nothing to override and the four survive intact. `Accept-Encoding` is not a hardcoded string — it is computed from the decoders actually installed, `", ".join(key for key in SUPPORTED_DECODERS if key != "identity")` ([_client.py#L120-L122](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L120-L122)). In this run that is `"gzip, deflate"`; with the optional `brotli` or `zstandard` packages present it would also advertise `br` and `zstd`. The client only ever asks for encodings it can undo.

Cookies become an empty `CookieJar`, params an empty `QueryParams`, and the timeout is coerced through `Timeout(Timeout(timeout=5.0))` — the module-level `DEFAULT_TIMEOUT_CONFIG` ([_config.py#L246](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_config.py#L246)), five seconds on each of connect, read, write and pool. `follow_redirects` stays `False` ([_client.py#L654](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L654)), `max_redirects` is 20, both event-hook lists are empty, and the state is set to `ClientState.UNOPENED` ([_client.py#L204-L221](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L204-L221)).

> **For the owner:** `follow_redirects` defaults to `False`, which differs from `requests`. Confirm that callers inspect `response.status_code` or `response.next_request` rather than assuming a 3xx was followed.

Back in `Client.__init__`, two lines decide the routing. `allow_env_proxies = trust_env and transport is None` ([_client.py#L685-L686](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L685-L686)) — and because an explicit transport was supplied, that is `False` even though `trust_env` is still `True`. So `_get_proxy_map(proxy=None, allow_env_proxies=False)` skips the `get_environment_proxies()` branch entirely and returns `{}` ([_client.py#L239-L251](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L239-L251)). `_mounts` is built from that empty map, no `mounts=` argument arrives to extend it, and `dict(sorted(...))` sorts nothing ([_client.py#L697-L716](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L697-L716)). An empty mount table is a guarantee: when the request later asks which transport should carry it, there is only one answer.

`_init_transport` confirms it. Its first two lines are `if transport is not None: return transport` ([_client.py#L728-L729](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L728-L729)) — so the `verify=True`, `cert`, `http1`/`http2` and `limits` arguments that were threaded all the way down are simply discarded, and no `HTTPTransport`, no SSL context and no `httpcore` pool is ever constructed. Had `transport` been `None`, this is where the real networking stack would have been built.

> **For the owner:** supplying `transport=` silently disables environment-variable proxying, because `allow_env_proxies` requires `transport is None`. If any deployment relies on `HTTP_PROXY`/`HTTPS_PROXY` while also passing a custom transport, that proxy will not be used; configure the proxy on the transport instead.

Finally the `with` block. `Client.__enter__` checks the state first and refuses anything other than `UNOPENED`, raising `RuntimeError("Cannot open a client instance more than once.")` or the reopen-after-close variant ([_client.py#L1275-L1283](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1275-L1283)). Our client is `UNOPENED`, so the state flips to `OPENED` and every transport is entered — here just the one, whose `BaseTransport.__enter__` returns itself and does nothing else ([base.py#L15-L16](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/base.py#L15-L16)). The client itself is returned to the caller.

The road is finished. At the far end of it sits a twelve-line Python function; between it and the caller there is a headers dict, a cookie jar, a timeout, a redirect policy and an empty mount table. `"/"` and `{"X-Custom": "value"}` are about to be handed in.

> **Leaves as:** an `OPENED` `Client` whose `_transport` **is** the caller's `WSGITransport`, `_mounts == {}`, `base_url == URL('http://testserver')` with `raw_path == b'/'`, default headers `Accept: */*` / `Accept-Encoding: gzip, deflate` / `Connection: keep-alive` / `User-Agent: python-httpx/0.28.1`, `Timeout(5.0)` on all four phases, `follow_redirects=False`, `max_redirects=20`
