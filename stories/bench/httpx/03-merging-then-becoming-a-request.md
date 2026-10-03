# Chapter 3 · Merging, then becoming a Request

> **Enters as:** `URL('http://testserver/')` from `_merge_url`, alongside `headers={'X-Custom': 'value'}`, `cookies=None`, `params=None`, `timeout=USE_CLIENT_DEFAULT`, `extensions=None`

`build_request` works through its arguments in order, and each one gets the same treatment: take whatever the client holds, take whatever the caller passed, and produce a single merged value ([_client.py#L366-L369](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L366-L369)). The URL has already been through that mill. The headers are next.

## Four defaults and one caller

`_merge_headers` copies the client's headers into a fresh `Headers` instance and then calls `.update()` with the caller's dict ([_client.py#L424-L431](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L424-L431)). The copy matters: the client's own `Headers` object is never mutated by a request, so concurrent requests on a shared client cannot scribble on each other's defaults.

`Headers.update` is not a plain extend. It builds a `Headers` from the argument, and for every key in it that already exists on the target, it *pops* the existing entry before appending the new list ([_models.py#L274-L279](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L274-L279)). In the trace you can watch the lookup happen: `keys()` on the incoming headers yields `dict_keys(['x-custom'])` — already lower-cased — and `__contains__('x-custom')` against the client's four defaults returns `False`, so nothing is popped. Every header is stored as a triple of `(raw_key, lower_key, value)`, so the wire casing `X-Custom` is preserved while comparisons use `x-custom` ([_models.py#L155-L162](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L155-L162), [_models.py#L346-L348](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L346-L348)).

Both the key and the value are coerced to bytes on the way in — `'X-Custom'` → `b'X-Custom'`, `'value'` → `b'value'` — using ASCII unless an explicit encoding was given ([_models.py#L67-L82](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L67-L82)). A non-str, non-bytes value raises `TypeError` here rather than failing somewhere down in the transport.

What comes back is `Headers({'accept': '*/*', 'accept-encoding': 'gzip, deflate', 'connection': 'keep-alive', 'user-agent': 'python-httpx/0.28.1', 'x-custom': 'value'})` — the four client defaults from chapter 1, plus the caller's one.

> **For the owner:** A per-request header replaces a client-level header of the same name case-insensitively, rather than being sent alongside it ([_models.py#L274-L279](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L274-L279)). If your client is configured with a credential header, a caller passing `headers={"authorization": ...}` silently overrides it. Decide whether that override is intended, and keep credentials in an `auth=` scheme rather than a default header if it is not.

## Two merges that decline to do anything

`_merge_cookies` is guarded: it only builds a merged jar `if cookies or self.cookies` ([_client.py#L418](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L418)). The argument is `None` and `Cookies.__bool__` on the client's empty jar returns `False` ([_models.py#L1228-L1231](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L1228-L1231)), so it returns `cookies` unchanged — `None`. No `Cookie:` header will be constructed for this request. That is the quiet half of httpx's cookie design: the client's jar, not the request, is the authority on cookies.

`_merge_queryparams` is shaped the same way ([_client.py#L440-L443](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L440-L443)). `QueryParams('')` on the client is falsy, the argument is `None`, so it returns `None` and the URL's query stays absent rather than becoming an empty `?`.

## The timeout becomes cargo

Now the one piece of configuration that travels *inside* the request. `extensions` is `None`, so it starts as `{}`; `"timeout"` is not in it, so the client's timeout is resolved. `timeout` is a `UseClientDefault` sentinel, so `self.timeout` wins — `Timeout(timeout=5.0)` — and `as_dict()` flattens it to `{'connect': 5.0, 'read': 5.0, 'write': 5.0, 'pool': 5.0}` ([_client.py#L371-L377](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L371-L377), [_config.py#L132-L138](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_config.py#L132-L138)). The dict is attached as `extensions={'timeout': ...}`.

Note the shape of the condition. If the caller had supplied their own `extensions` containing a `"timeout"` key, the entire block is skipped and the client-level timeout never appears — caller-supplied extensions win outright, with no merge.

> **For the owner:** Passing `extensions={"timeout": ...}` suppresses the client's configured timeout for that request entirely ([_client.py#L371](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L371)). Grep for `extensions=` in calling code and confirm each occurrence either carries a complete timeout dict or deliberately disables timeouts. Note also that this step only *records* the timeout on the request; nothing here enforces it.

## Becoming a Request

With all four merged values in hand, `build_request` constructs the `Request` ([_client.py#L378-L389](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L378-L389)).

The constructor uppercases the method to `'GET'`, re-wraps the URL (a `copy_with()` with no changes, returning the same components), and copies the headers again into the request's own `Headers` ([_models.py#L398-L401](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L398-L401)). `self.extensions = dict(extensions)` is likewise a copy, so the dict the client built cannot be mutated out from under the request. The `cookies` branch is skipped, since cookies is `None` ([_models.py#L403-L404](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L403-L404)).

`stream` is `None`, so the body is encoded. First a `content-type` lookup, which returns `None`, so `get_multipart_boundary_from_content_type(None)` returns `None` ([_models.py#L407-L418](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L407-L418), [_multipart.py#L56-L67](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_multipart.py#L56-L67)) — that lookup exists so that a caller who sets their own multipart content-type gets their boundary honoured rather than a fresh random one.

`encode_request` then walks its cascade — `data`, `content`, `files`, `data`, `json` — and reaches the bottom with all of them `None`, returning `({}, ByteStream(b""))` ([_content.py#L186-L218](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_content.py#L186-L218)). No content headers at all: no Content-Type, no Content-Length. (Had the caller passed `data=b"..."`, the first branch would have rerouted it to `encode_content` with a `DeprecationWarning` — a `requests` compatibility shim, not the intended API ([_content.py#L197-L207](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_content.py#L197-L207)).)

## `_prepare`: the headers the caller didn't write

`_prepare` receives that empty default-header dict, so its `setdefault` loop does nothing — including the branch that drops a `Transfer-Encoding` default when `Content-Length` was set explicitly, which exists to stop the two framing headers from contradicting each other ([_models.py#L442-L446](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L442-L446)).

Then three membership checks, visible in the trace as one `__contains__` plus two more: `Host`, `Content-Length`, `Transfer-Encoding`. All absent. So `Host` is auto-added from `url.netloc` — `b'testserver'` ([_models.py#L450-L456](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L450-L456)) — and `Content-Length: 0` is *not*, because that is only added for `POST`, `PUT` and `PATCH` ([_models.py#L457-L458](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L457-L458)). A GET with no body therefore goes out with no framing header at all.

The final line rebuilds the header list as `auto_headers + self.headers.raw` ([_models.py#L460](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L460)), which is why `Host` lands first and the caller's ordering is otherwise preserved: `Host, Accept, Accept-Encoding, Connection, User-Agent, X-Custom`.

> **For the owner:** `Host` is derived from the URL only when the caller did not supply one ([_models.py#L450-L456](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L450-L456)). A caller-supplied `Host` header overrides it while the connection target still comes from the URL, which changes virtual-host routing on the server. Treat a user-controllable `Host` header as a routing control, not a cosmetic one.

## Read before it leaves

Last, because the stream is a `ByteStream`, the constructor reads it immediately ([_models.py#L422-L423](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L422-L423)). `read()` joins the stream into `self._content = b''` ([_models.py#L468-L480](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L468-L480)). An in-memory body is buffered up front so that `request.content` is always available and the body can be sent more than once; a generator or file-iterator body would have been left lazy, and would be unrepeatable.

`build_request` returns `<Request('GET', 'http://testserver/')>` to `request()`, which passes it straight to `send()`.

> **Leaves as:** `<Request('GET', 'http://testserver/')>` — method `'GET'`, headers raw `[(b'Host', b'testserver'), (b'Accept', b'*/*'), (b'Accept-Encoding', b'gzip, deflate'), (b'Connection', b'keep-alive'), (b'User-Agent', b'python-httpx/0.28.1'), (b'X-Custom', b'value')]`, `stream=ByteStream(b'')`, `_content == b''`, `extensions == {'timeout': {'connect': 5.0, 'read': 5.0, 'write': 5.0, 'pool': 5.0}}`
