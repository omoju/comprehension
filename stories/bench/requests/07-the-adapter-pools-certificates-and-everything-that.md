# Chapter 7 · The Adapter: Pools, Certificates, and Everything That Can Go Wrong

> **Enters as:** `HTTPAdapter.send(request=<PreparedRequest [GET]>, stream=False, timeout=None, verify=True, cert=None, proxies=OrderedDict())`

The request crosses out of `sessions.py` and into the one object that knows about sockets. `HTTPAdapter.send` is a long function, and almost all of its length is spent on things that did not happen here: proxies, TLS, timeouts, and a catalogue of failures ([adapters.py#L634-L748](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L634-L748)).

It opens with the same type-narrowing `assert _is_prepared(request)` the Session used — the trace shows `is_prepared → True`, as it does for every argument — and then asks for a connection ([adapters.py#L659-L666](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L659-L666)).

## Finding a pool, and what the pool key remembers

`get_connection_with_tls_context(request, verify=True, proxies=OrderedDict(), cert=None)` ([adapters.py#L455-L510](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L455-L510)) first repeats the proxy question the Session already answered: `select_proxy(request.url, proxies)` walks four candidate keys — `http://127.0.0.1`, `http`, `all://127.0.0.1`, `all` — against the empty dict ([utils.py#L885-L908](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L885-L908)). The trace records `→ None`. Had it returned a proxy, the request would have been routed through `proxy_manager_for(proxy)` instead, and a malformed proxy URL with no host would have raised `InvalidProxyURL` ([adapters.py#L492-L503](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L492-L503)).

Then it builds the key that decides *which* pooled connection this request may use. `build_connection_pool_key_attributes` is a thin public wrapper, documented as the subclassing hook for custom `SSLContext` work, over `_urllib3_request_context` ([adapters.py#L403-L453](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L403-L453)). That function parses the URL and assembles two dicts ([adapters.py#L85-L119](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L85-L119)):

```
({'host': '127.0.0.1', 'port': 54897, 'scheme': 'http'}, {'cert_reqs': 'CERT_REQUIRED'})
```

The first is the host identity. The second is the TLS posture: `cert_reqs` starts at `"CERT_REQUIRED"` and is downgraded to `"CERT_NONE"` only when `verify is False`; a string `verify` becomes `ca_certs` or, if it names a directory, `ca_cert_dir`; a `cert` tuple becomes `cert_file` plus `key_file` ([adapters.py#L97-L113](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L97-L113)). Those second-dict entries are passed to urllib3 as `pool_kwargs`, which means they are part of the pool key — two requests to the same host with different `verify` or `cert` settings get *different* pools. A connection established under a relaxed setting cannot be silently handed to a request that asked for a strict one.

Note what this says about our request. The scheme is `http`; `cert_reqs: CERT_REQUIRED` is set anyway, and will mean nothing, because there is no TLS handshake to apply it to. The trace returns `<urllib3.connectionpool.HTTPConnectionPool object at 0x10da09400>`.

If URL parsing had failed with a `ValueError` here, or if urllib3 had raised `LocationValueError` on the way out, both would surface as `requests.exceptions.InvalidURL` carrying the request ([adapters.py#L490-L491](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L490-L491), [adapters.py#L665-L666](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L665-L666)).

## cert_verify: where the TLS promise lives, and where it doesn't

`self.cert_verify(conn, request.url, verify, cert)` ([adapters.py#L307-L363](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L307-L363)) is the function an owner should read if they read only one in this chapter. Its first line is the whole story:

```python
if url.lower().startswith("https") and verify:
```
([adapters.py#L321](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L321))

For an `https` URL with a truthy `verify`, this is where the default trust store is resolved — `verify=True` falls through to `DEFAULT_CA_BUNDLE_PATH`, which is certifi's bundle, and a missing or nonexistent path raises `OSError` with the offending location named, before any connection attempt ([adapters.py#L322-L342](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L322-L342), [utils.py#L81-L82](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L81-L82)).

Our URL starts with `http`, so the `else` branch ran ([adapters.py#L343-L346](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L343-L346)):

```python
conn.cert_reqs = "CERT_NONE"
conn.ca_certs = None
conn.ca_cert_dir = None
```

The `verify=True` that survived two merges in Chapter 6 has just been set aside, correctly and quietly, because there is nothing to verify. `cert` is `None`, so the client-certificate block — which checks that the cert file and key file exist and raises `OSError` naming each if not ([adapters.py#L348-L363](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L348-L363)) — is skipped entirely. The trace shows `cert_verify → None` with nothing underneath it.

> **For the owner:** `verify` has no effect on `http://` URLs; certificate and hostname checking exist only on the TLS path. Confirm that any request carrying credentials uses an `https://` URL, because the `Authorization: Basic dXNlcjpwYXNz` header on this request is base64, not encryption, and goes out in clear text on the wire.

## The request line, and a header dict urllib3 is about to copy

`request_url(request, proxies)` decides what goes after the verb ([adapters.py#L565-L597](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L565-L597)). It asks `select_proxy` a second time (`None` again), reads the scheme, and takes the default path:

```python
url = request.path_url
```

`path_url` splits the prepared URL and joins path and query, substituting `/` for an empty path ([models.py#L111-L130](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L111-L130)). The trace: `'/basic-auth/user/pass'`. Only a proxied non-HTTPS request would have used the absolute form, and then through `urldefragauth`, which strips the fragment *and* any `user:pass@` from the netloc so credentials embedded in a URL are not handed to a proxy ([adapters.py#L594-L595](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L594-L595), [utils.py#L1122-L1136](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L1122-L1136)).

`add_headers` is called next with every send kwarg and does nothing at all — it is `pass`, documented as an override point for subclasses that need per-connection headers ([adapters.py#L599-L611](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L599-L611)).

Then one line that answers a question left open two chapters ago:

```python
chunked = not (request.body is None or "Content-Length" in request.headers)
```
([adapters.py#L679](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L679))

`request.body` is `None`, so `chunked` is `False`. The GET goes out with neither `Content-Length` nor `Transfer-Encoding` — a bodiless request, exactly as `prepare_content_length` intended.

## timeout=None becomes a Timeout that never fires

```python
else:
    resolved_timeout = TimeoutSauce(connect=timeout, read=timeout)
```
([adapters.py#L681-L693](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L681-L693))

A tuple would have been unpacked into `(connect, read)`, with a malformed tuple rejected by a `ValueError` whose message tells the caller the two accepted shapes. An already-built urllib3 `Timeout` would pass through. Ours is `None`, so `TimeoutSauce(connect=None, read=None)`: no connect deadline, no read deadline.

And the retry budget was fixed back in Chapter 1: `HTTPAdapter.__init__` saw the default `max_retries=0` and built `Retry(0, read=False)` ([adapters.py#L208-L211](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L208-L211)).

> **For the owner:** With no `timeout` argument this call can block indefinitely, and `max_retries=0` means there is no retry budget bounding it either. Require an explicit `timeout` on every outbound request in code you sign off on.

## The one call that touches the network

```python
resp = conn.urlopen(
    method=request.method,
    url=url,
    body=request.body,
    headers=request.headers,
    redirect=False,
    assert_same_host=False,
    preload_content=False,
    decode_content=False,
    retries=self.max_retries,
    timeout=resolved_timeout,
    chunked=chunked,
)
```
([adapters.py#L695-L708](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L695-L708))

Four of those keywords are a division of labour. `redirect=False` and `retries=self.max_retries` keep redirect-following and retrying in Requests' own hands, where `resolve_redirects` can strip credentials and `Response.history` can record hops. `preload_content=False` means urllib3 returns as soon as it has parsed the status line and headers — the body stays on the socket. `decode_content=False` means gzip and deflate are not unwrapped here either; that happens later, when Requests reads the stream.

Inside urllib3, the trace shows our headers being handled: `CaseInsensitiveDict.copy()` builds a fresh dict from the stored `(cased key, value)` pairs ([structures.py#L89-L90](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/structures.py#L89-L90)) — five entries this time, the four defaults plus `'Authorization': 'Basic dXNlcjpwYXNz'` — and is then iterated and read key by key. The original casing survives the round trip; that is the whole point of storing the cased key alongside the value.

A socket opens to 127.0.0.1:54897, the request line and five headers go out, and `conn.urlopen` returns `<urllib3.response.HTTPResponse object at 0x10c23f910>` with its body unread.

## The failures that didn't happen

Nothing in this run entered the `except` blocks, but they are the adapter's contract with the caller, so they are worth naming ([adapters.py#L710-L746](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L710-L746)). Every urllib3 or OS error that this layer recognises is re-raised as a `requests.exceptions` type carrying `request=request`:

- `ProtocolError` or any `OSError` → `ConnectionError`
- `MaxRetryError`, dispatched on `e.reason`: `ConnectTimeoutError` (but not `NewConnectionError`) → `ConnectTimeout`; `ResponseError` → `RetryError`; urllib3 `ProxyError` → `ProxyError`; urllib3 `SSLError` → `SSLError`; anything else → `ConnectionError`
- `ClosedPoolError` → `ConnectionError`; bare `_ProxyError` → `ProxyError`
- `_SSLError` → `SSLError`, `ReadTimeoutError` → `ReadTimeout`, `_InvalidHeader` → `InvalidHeader`, and any other `_HTTPError` is **re-raised unchanged** ([adapters.py#L745-L746](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L745-L746))

> **For the owner:** Catch `requests.exceptions.RequestException` for transport failures, but do not assume it covers everything — an unrecognised `urllib3.exceptions.HTTPError` escapes this layer as itself. Note also that a 4xx or 5xx status raises nothing here; only `raise_for_status()` turns a status code into an exception.

One line remains in `send`: `return self.build_response(request, resp)` ([adapters.py#L748](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L748)). The urllib3 response — status parsed, headers parsed, body still on the wire — is about to be dressed as a `requests.Response`.

> **Leaves as:** a live `<urllib3.response.HTTPResponse object at 0x10c23f910>` (status 200, body unread), returned from `conn.urlopen` after `'GET /basic-auth/user/pass'` was sent with five headers including `Authorization: Basic dXNlcjpwYXNz`, about to enter `build_response(req, resp)`
