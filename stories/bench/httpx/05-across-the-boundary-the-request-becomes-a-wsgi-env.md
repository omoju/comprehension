# Chapter 5 · Across the boundary: the request becomes a WSGI environ

> **Enters as:** `<Request('GET', 'http://testserver/')>` with headers `Host: testserver`, `Accept: */*`, `Accept-Encoding: gzip, deflate`, `Connection: keep-alive`, `User-Agent: python-httpx/0.28.1`, `X-Custom: value`, body `b''`, handed to `WSGITransport.handle_request`

This is the boundary. Above it, everything was `httpx` types; below it, the request has to become a plain dictionary and a callback, because that is the only vocabulary a WSGI application speaks.

## Flattening the request

The first two lines of `handle_request` read the body and wrap it ([wsgi.py#L92-L93](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L92-L93)):

```
request.read()
wsgi_input = io.BytesIO(request.content)
```

`request.read()` finds `_content` already set from chapter 3 and returns `b''` immediately ([_models.py#L468-L480](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L468-L480)); `request.content` then hands back the same `b''` ([_models.py#L462-L466](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L462-L466)). The empty body becomes a `BytesIO` with nothing in it.

> **For the owner:** This transport buffers the entire request body in memory before calling the application ([wsgi.py#L92-L93](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L92-L93)). Do not use `WSGITransport` to exercise large-upload paths; it defeats the streaming behaviour you would get from a real transport.

Then the port. `request.url.port` is `None` — chapter 2 normalised the absent `:80` away — so the fallback table supplies it ([wsgi.py#L95](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L95)):

```
port = request.url.port or {"http": 80, "https": 443}[request.url.scheme]
```

The trace shows `URL.port → None` and `URL.scheme → 'http'`, giving `port = 80`. Note that this is a bare dictionary subscript: a URL with any other scheme — `ftp://`, or a custom one mounted onto this transport — would raise `KeyError` here rather than an `httpx` exception.

The environ dict is assembled from the URL's parts ([wsgi.py#L96-L112](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L96-L112)). The trace walks each accessor in order: `URL.path → '/'` becomes `PATH_INFO`, `URL.query → b''` is decoded to `''` for `QUERY_STRING`, `URL.host → 'testserver'` becomes `SERVER_NAME`. `REQUEST_METHOD` is `'GET'`, `SCRIPT_NAME` is `''` (the transport's default), `REMOTE_ADDR` is `'127.0.0.1'`, `SERVER_PROTOCOL` is the hardcoded string `'HTTP/1.1'`.

This answers a question from chapter 2. Nothing resolves `testserver`. The hostname is copied into the environ as metadata and carried in the `Host` header; no socket is opened, no DNS lookup happens, no TLS handshake occurs. The name only ever has to satisfy the application.

Headers follow, uppercased and underscored per the WSGI convention ([wsgi.py#L113-L117](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L113-L117)):

```
for header_key, header_value in request.headers.raw:
    key = header_key.decode("ascii").upper().replace("-", "_")
    if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
        key = "HTTP_" + key
    environ[key] = header_value.decode("ascii")
```

`request.headers.raw` returns the six pairs built in chapter 3, `Host` first ([_models.py#L195-L200](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L195-L200)). The caller's `X-Custom: value` arrives at the application as `environ["HTTP_X_CUSTOM"] == "value"`. `CONTENT_TYPE` and `CONTENT_LENGTH` are exempted from the prefix because WSGI specifies them bare — neither is present on this GET.

## Calling the application

Three `nonlocal` variables are declared and a `start_response` closure is defined to capture them ([wsgi.py#L119-L132](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L119-L132)). Then, in one line, the whole request crosses over ([wsgi.py#L134](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L134)):

```
result = self.app(environ, start_response)
```

The application runs synchronously, in this thread, on this stack. It asserts the method and path, then calls back: `start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', '12')], exc_info=None)`. The closure stores all three into `seen_status`, `seen_response_headers`, `seen_exc_info` and returns a throwaway `lambda _: None` — the legacy `write()` callable, which this transport does not support. The app then returns `[b'Hello World!']`.

Nothing here consults `request.extensions['timeout']`. The five-second budget assembled in chapter 3 and verified in chapter 4 travels all the way down and is simply never read. That answers the question left open in chapter 3: on this path, nobody enforces the timeout. A WSGI application that loops forever hangs the caller.

> **For the owner:** `WSGITransport` ignores the request's timeout extension entirely ([wsgi.py#L91-L149](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L91-L149)); timeouts are enforced by the network transports, not by the client core. Do not rely on tests that use this transport to prove your timeout configuration works.

## Checking what came back

```
assert seen_status is not None
assert seen_response_headers is not None
if seen_exc_info and seen_exc_info[0] and self.raise_app_exceptions:
    raise seen_exc_info[1]
```

([wsgi.py#L138-L141](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L138-L141).) An application that returns without calling `start_response` trips a bare `AssertionError` — not an `httpx` exception. And since chapter 4's `request_context` only stamps `.request` onto `RequestError` subclasses and re-raises everything else untouched ([_exceptions.py#L364-L377](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_exceptions.py#L364-L377)), that `AssertionError` — and any exception the application itself raises and reports through `exc_info` — propagates out of `client.get()` raw and unwrapped. That answers chapter 4's open question: the context manager guarantees almost nothing about application-level failures.

`raise_app_exceptions` defaults to `True` ([wsgi.py#L80](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L80)), which is why an application bug surfaces as that bug rather than as a 500 response. Setting it `False` is what lets a test inspect the body of a 500 instead.

> **For the owner:** Exceptions raised inside the WSGI application are re-raised to the caller by default, and they are not `httpx` exception types ([wsgi.py#L140-L141](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L140-L141)). Code that catches `httpx.HTTPError` around a WSGI-transport call will not catch them.

## Becoming a Response

The status line is split and parsed, the headers encoded ([wsgi.py#L143-L147](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L143-L147)):

```
status_code = int(seen_status.split()[0])
headers = [
    (key.encode("ascii"), value.encode("ascii"))
    for key, value in seen_response_headers
]
```

`'200 OK'` becomes `200`; the two header tuples become `[(b'Content-Type', b'text/plain; charset=utf-8'), (b'Content-Length', b'12')]`. Both steps are strict: a malformed status string gives `ValueError`, a non-ASCII header name or value gives `UnicodeEncodeError`, and neither is caught.

Before that, the app's return value was wrapped ([wsgi.py#L136](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L136)). `WSGIByteStream.__init__` squirrels away `getattr(result, "close", None)` — a plain list has none, so `_close` is `None` — and passes the iterable through `_skip_leading_empty_chunks` ([wsgi.py#L30-L33](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L30-L33)). That helper pulls items until it finds a truthy one and chains it back on front ([wsgi.py#L22-L27](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L22-L27)), so an application that yields `b''` before its real content does not look like an empty body. The trace shows it returning an `itertools.chain` object.

Finally ([wsgi.py#L149](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L149)):

```
return Response(status_code, headers=headers, stream=stream)
```

The `stream=` form is deliberate. `Response.__init__` takes the branch that assigns `self.stream = stream` and stops ([_models.py#L555-L567](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L555-L567)) — no `_prepare`, no auto-populated content headers, no eager `read()`. The body stays lazy; only the headers the application actually sent are present. The trace shows just the `Headers.__init__` call and its four normalisation calls, then `→ <Response [200 OK]>`.

The response that comes back has no `.request` attached, no `http_version` or `reason_phrase` extension, and an unread stream. Those gaps are the client's to fill.

> **Leaves as:** `<Response [200 OK]>` with `headers = Headers({'content-type': 'text/plain; charset=utf-8', 'content-length': '12'})`, `stream = <WSGIByteStream>` over `[b'Hello World!']`, `extensions = {}`, `_request = None`, body unread
