# Chapter 6 · Dressing the response, then unwinding the redirect and auth loops

> **Enters as:** `<Response [200 OK]>` with `headers = Headers({'content-type': 'text/plain; charset=utf-8', 'content-length': '12'})`, `stream = <WSGIByteStream>` over `[b'Hello World!']`, `extensions = {}`, `_request = None`, body unread — returned from the transport back into `Client._send_single_request`

The response is back on the `httpx` side of the boundary, but it is not yet a response the caller would recognise. It knows nothing about the request that produced it, nothing about how long it took, and its headers have not been shown to the cookie jar. The rest of `_send_single_request` is the dressing room.

## First, the contract check

Control returns from the `with request_context(...)` block and lands on an assertion ([_client.py#L1016](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1016)):

```
assert isinstance(response.stream, SyncByteStream)
```

`WSGIByteStream` subclasses `SyncByteStream` ([wsgi.py#L30](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L30)), so this passes. It is the mirror of the check on the way down: chapter 4 refused to send an async request body through a sync client, and here a transport that handed back an async stream would be caught before anything else touched the response.

## Attaching the request, and the stopwatch

```
response.request = request
response.stream = BoundSyncStream(
    response.stream, response=response, start=start
)
```

([_client.py#L1018-L1021](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1018-L1021).) The trace shows the setter at `_models.py:606` assigning `_request`, then `BoundSyncStream.__init__(stream=<WSGIByteStream>, response=<Response [200 OK]>, start=428800.362486125)`.

That `start` is the `time.perf_counter()` reading taken in chapter 4, *before* the transport was called ([_client.py#L1006](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1006)). `BoundSyncStream` exists for exactly one reason: it wraps the transport's stream so that when the body is eventually closed, the elapsed time is computed and stamped onto the response ([_client.py#L139-L159](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L139-L159)):

```
def close(self) -> None:
    elapsed = time.perf_counter() - self._start
    self._response.elapsed = datetime.timedelta(seconds=elapsed)
    self._stream.close()
```

The request attachment is load-bearing. Without it, `response.url`, `response.raise_for_status()` and the cookie extraction that is about to happen would all raise `RuntimeError("The request instance has not been set on this response.")` ([_models.py#L595-L604](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L595-L604)). That answers chapter 5's question about the empty `_request`: the client fills it in, one line after the transport returns.

## The cookie jar, before the body

```
self.cookies.extract_cookies(response)
```

([_client.py#L1022](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1022).) This happens as soon as the headers exist and well before the body is read. `extract_cookies` builds two compatibility shims and hands them to the stdlib `CookieJar` ([_models.py#L1101-L1108](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L1101-L1108)).

The trace shows both being constructed. `_CookieCompatResponse` just wraps the response ([_models.py#L1267-L1268](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L1267-L1268)). `_CookieCompatRequest` is heavier: it subclasses `urllib.request.Request`, which means `str(request.url)` is computed (`'http://testserver/'`) and `dict(request.headers)` is materialised — hence the burst of `Headers.keys`, `Headers.encoding` and `Headers.__getitem__` calls in the trace, one per header ([_models.py#L1249-L1255](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L1249-L1255)). Then `info()` converts the response headers into an `email.message.Message` so the jar can read `Set-Cookie` from them ([_models.py#L1270-L1277](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L1270-L1277)).

Our application sent no `Set-Cookie`, so the jar is still empty afterwards. But the plumbing matters: cookies land in the **client's** jar, not the response's, and they persist for every subsequent request on this client.

> **For the owner:** Any `Set-Cookie` the application returns is written into the client's shared cookie jar and will be sent on later requests through the same client ([_client.py#L1022](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1022)). Use a fresh `Client` per test case, or per security principal, if cross-request cookie leakage would be a problem.

## Degrading gracefully on missing extensions

```
response.default_encoding = self._default_encoding
```

([_client.py#L1023](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1023).) The client's text-decoding policy — `'utf-8'` here — is attached per response, not baked in at construction. That is what chapter 8 will consult.

Then the log line ([_client.py#L1025-L1032](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1025-L1032)), which pulls two properties the transport never set:

```
logger.info(
    'HTTP Request: %s %s "%s %d %s"',
    request.method, request.url,
    response.http_version, response.status_code, response.reason_phrase,
)
```

The trace shows `Response.http_version → 'HTTP/1.1'` and `Response.reason_phrase → 'OK'`. Neither came from the application. `http_version` reads `extensions["http_version"]` and, on `KeyError`, returns the literal `"HTTP/1.1"` ([_models.py#L610-L617](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L610-L617)). `reason_phrase` does the same and falls back to the status-code table, `codes.get_reason_phrase(200) → 'OK'` ([_models.py#L619-L626](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L619-L626), [_status_codes.py#L38-L43](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_status_codes.py#L38-L43)). So the response reports an HTTP version it never negotiated — an honest default, but a default.

> **For the owner:** The client logs every request at INFO on the `"httpx"` logger, including the full URL with its query string ([_client.py#L1025-L1032](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1025-L1032)). Check that no secrets are passed as query parameters, or configure that logger before shipping.

`_send_single_request` returns the dressed response.

## The redirect loop, which does not loop

Back in `_send_handling_redirects`, the response enters a `try` block whose `except BaseException` closes it and re-raises ([_client.py#L980-L999](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L980-L999)). The response-hook list is empty, so nothing runs; `response.history = list(history)` sets `[]`. Then the decision ([_client.py#L985-L986](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L985-L986)):

```
if not response.has_redirect_location:
    return response
```

`has_redirect_location` wants two things at once: a status in `{301, 302, 303, 307, 308}` *and* a `Location` header ([_models.py#L771-L792](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L771-L792)). Status 200 fails the first test, so the trace shows `→ False` and the response is handed straight back.

Two roads not taken are worth naming, because they are where the interesting guarantees live.

Had this been a 302 *with* a Location header, `follow_redirects` resolved to `False` in chapter 4 — so the client would not raise and would not fetch anything. It would build the follow-up request, hang it on `response.next_request`, and return the 302 to the caller ([_client.py#L988-L995](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L988-L995)). That answers chapter 1's question: the default is deliberately unlike `requests` — redirects are visible, not silent.

And had redirects been followed to a different origin, `_redirect_headers` would have rewritten the header set ([_client.py#L546-L571](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L546-L571)): `Authorization` popped (except for a plain http→https upgrade of the same host), `Host` rewritten to the new netloc, `Content-Length` and `Transfer-Encoding` dropped if the method flipped to GET, and `Cookie` always dropped so the client jar is the single source of cookie truth. A custom header like `X-Custom` is **not** stripped — it follows the redirect to the new origin. That answers chapter 3's question, and it is the one worth flagging.

> **For the owner:** On a cross-origin redirect the client strips `Authorization` and `Cookie` but carries every other header, including custom ones, to the new host ([_client.py#L552-L569](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L552-L569)). Audit any header you use to carry a credential, such as `X-Api-Key`, and set it per-request rather than on the client if redirects are followed.

Also note that the loop is bounded by construction: `len(history) > self.max_redirects` raises `TooManyRedirects` at the top of every iteration, default 20 ([_client.py#L970-L974](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L970-L974)).

## The auth generator, resumed and exhausted

The response surfaces in `_send_handling_auth`, which pushes it back into the generator ([_client.py#L947-L951](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L947-L951)):

```
try:
    next_request = auth_flow.send(response)
except StopIteration:
    return response
```

`sync_auth_flow` is sitting at `response = yield request`. `requires_response_body` is `False` on the base `Auth`, so no read happens ([_auth.py#L77-L80](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_auth.py#L77-L80)). It calls `flow.send(response)` on the inner `auth_flow`, which has nothing left after its single `yield request` ([_auth.py#L38-L60](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_auth.py#L38-L60)) — the trace shows both generators returning `None` — and `break`s out of its `while True` ([_auth.py#L82-L85](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_auth.py#L82-L85)). The outer `send()` raises `StopIteration`, caught, and the response is returned.

Had the flow yielded a second request — a digest challenge, a token refresh — the path would have been different: `response.history = list(history)`, then `response.read()` to buffer it entirely, then append to history and loop ([_client.py#L953-L956](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L953-L956)). A multi-step auth scheme therefore implies buffering every intermediate response in memory. The `finally: auth_flow.close()` guarantees the generator is finalised either way ([_client.py#L961-L962](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L961-L962)).

The response leaves `_send_handling_auth` with its body still untouched.

> **Leaves as:** `<Response [200 OK]>` with `.request` set to `<Request('GET', 'http://testserver/')>`, `.stream` a `BoundSyncStream` wrapping the `WSGIByteStream`, `.default_encoding == 'utf-8'`, `.history == []`, `.next_request is None`, `.http_version == 'HTTP/1.1'`, `.reason_phrase == 'OK'`, body unread and `is_closed is False`
