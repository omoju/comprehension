# Chapter 7 · Reading the body: decoders, chunker, and the close that sets elapsed

> **Enters as:** `<Response [200 OK]>` with `.request` set, `.stream` a `BoundSyncStream` wrapping a `WSGIByteStream` over `[b'Hello World!']`, `.default_encoding == 'utf-8'`, no `_content` attribute, `is_stream_consumed is False`, `is_closed is False`

Back in `Client.send`, the response hits the one line that decides whether the body is the caller's problem or the client's ([_client.py#L920-L928](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L920-L928)):

```
try:
    if not stream:
        response.read()
    return response
except BaseException as exc:
    response.close()
    raise exc
```

`stream` is `False` — `client.get()` never passes it — so `read()` runs, and it runs inside a handler that closes the response if anything goes wrong. That is the guarantee: on this path, a failure during the read cannot leave a stream dangling.

## read(), which is a join over an iterator

```
def read(self) -> bytes:
    if not hasattr(self, "_content"):
        self._content = b"".join(self.iter_bytes())
    return self._content
```

([_models.py#L876-L882](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L876-L882).) Note the shape: the whole body is accumulated into one `bytes` object with no size cap anywhere. For a twelve-byte "Hello World!" that is nothing. For an application that returns a gigabyte, it is a gigabyte of client-side memory.

> **For the owner:** `response.read()` buffers the entire decoded body into memory with no limit ([_models.py#L880-L882](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L880-L882)), and the non-streaming `client.get()` path always calls it ([_client.py#L921-L922](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L921-L922)). Use `client.stream(...)` and `iter_bytes()` for any endpoint whose response size you do not control.

## Choosing a decoder from a header that isn't there

`iter_bytes` checks for `_content` first; it is absent, so the decoding path opens ([_models.py#L889-L905](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L889-L905)). First it asks for a decoder.

`_get_content_decoder` reads the response's `content-encoding` headers with `split_commas=True`, so `"gzip, br"` would arrive as two separate names ([_models.py#L699-L722](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L699-L722)). Our application sent none — the trace shows `Headers.get_list(key='content-encoding', split_commas=True) → []` — so no decoders are collected and the `else` branch produces an `IdentityDecoder`, whose `decode` returns its argument untouched ([_decoders.py#L44-L53](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L44-L53)).

The branches not taken here are worth knowing, because two of them are policy decisions:

- An encoding name that isn't in `SUPPORTED_DECODERS` is **silently skipped** (`except KeyError: continue`, [_models.py#L709-L713](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L709-L713)). The bytes then pass through undecoded rather than raising.
- Several valid encodings compose into a `MultiDecoder`, which applies them in reverse order ([_models.py#L715-L720](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L715-L720), [_decoders.py#L203-L225](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L203-L225)).
- A corrupt gzip or deflate body raises `DecodingError` ([_decoders.py#L95-L105](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L95-L105)) — and because the decode loop runs inside `with request_context(request=self._request)` ([_models.py#L896](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L896)), that error arrives with `.request` attached. `DecodingError` is a `RequestError`, so unlike the raw application exceptions of chapter 5, this one does get tagged.

Recall that the client advertised `Accept-Encoding: gzip, deflate` back in chapter 1, derived from `SUPPORTED_DECODERS` minus `identity` ([_client.py#L120-L122](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L120-L122)). The client only asks for what it can undo.

Next a `ByteChunker(chunk_size=None)` is built ([_models.py#L895](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L895), [_decoders.py#L233-L235](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L233-L235)). With no chunk size it is a pass-through that drops empties: `return [content] if content else []` ([_decoders.py#L238-L239](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L238-L239)). It earns its keep only when the caller asked for fixed-size chunks.

## iter_raw: three refusals, then the bytes

`iter_bytes` now pulls from `iter_raw()`, which begins with three guards ([_models.py#L939-L944](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L939-L944)):

```
if self.is_stream_consumed:
    raise StreamConsumed()
if self.is_closed:
    raise StreamClosed()
if not isinstance(self.stream, SyncByteStream):
    raise RuntimeError("Attempted to call a sync iterator on an async stream.")
```

All three are false for a fresh response, so it proceeds — setting `is_stream_consumed = True` and resetting `_num_bytes_downloaded` to `0` ([_models.py#L946-L947](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L946-L947)). Those guards are what makes "read the body twice" a clean error rather than a silently empty result.

Inside its own `request_context`, it iterates `self.stream` — the `BoundSyncStream`, which simply forwards from the `WSGIByteStream` ([_client.py#L152-L154](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L152-L154), [wsgi.py#L35-L37](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L35-L37)). The trace shows one chunk coming through: `b'Hello World!'`. `_num_bytes_downloaded` grows by `12` ([_models.py#L952](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L952)) — counted on the *raw*, pre-decode bytes, which is precisely why it is the right basis for a download progress bar on a compressed response.

The chunker yields it through unchanged (`→ [b'Hello World!']`), the decoder's `IdentityDecoder.decode` returns it unchanged, and `iter_bytes`'s own chunker yields it to `read()`'s `join`.

## The close that sets elapsed

When the `WSGIByteStream` is exhausted, `iter_raw` runs its last statement ([_models.py#L956-L959](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L956-L959)):

```
for chunk in chunker.flush():
    yield chunk

self.close()
```

The flush is empty — the chunker held nothing back. Then `close()` sets `is_closed = True` and calls `self.stream.close()` inside another `request_context` ([_models.py#L961-L972](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L961-L972)).

That is the `BoundSyncStream.close` from chapter 6, and here is where the stopwatch finally stops ([_client.py#L156-L159](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L156-L159)):

```
elapsed = time.perf_counter() - self._start
self._response.elapsed = datetime.timedelta(seconds=elapsed)
self._stream.close()
```

So `elapsed` spans from just before the WSGI app was invoked to just after its body was fully consumed — not merely the transport call. Reading the body is part of the measurement.

The delegation continues down to `WSGIByteStream.close`, which calls the application iterable's `close` if it captured one ([wsgi.py#L31-L41](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L31-L41)):

```
def __init__(self, result):
    self._close = getattr(result, "close", None)
...
def close(self):
    if self._close is not None:
        self._close()
```

Our app returned a plain `list`, which has no `close`, so `self._close` is `None` and this is a no-op. A generator-based or file-backed WSGI app would be properly closed here — which answers chapter 5's question about that captured attribute.

> **For the owner:** `response.elapsed` is only assigned when the response stream is closed ([_client.py#L156-L158](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L156-L158)); reading it earlier raises `RuntimeError` ([_models.py#L584-L589](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L584-L589)). Do not use it as a server-latency metric, because it includes the time your own code spent consuming the body.

The trace records one more entry — `… Response.iter_bytes ×1 more` — the generator being resumed once to confirm exhaustion before `join` completes. `read()` assigns `self._content = b'Hello World!'` and returns it. `Client.send` returns the response, `Client.request` returns it, `Client.get` returns it, and it reaches the caller's `response` variable at last.

> **Leaves as:** `<Response [200 OK]>` with `_content == b'Hello World!'`, `num_bytes_downloaded == 12`, `is_stream_consumed is True`, `is_closed is True`, `elapsed` set to a `datetime.timedelta`, `.request` still `<Request('GET', 'http://testserver/')>`
