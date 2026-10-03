# Chapter 10 · Reading the Body, Closing Everything, and Decoding What Came Back

> **Enters as:** `<Response [200]>` with `_content = False`, `_content_consumed = False`, `encoding = 'utf-8'`, and a live urllib3 stream at `raw` — one line from the end of `Session.send`

Two statements remain:

```python
        if not stream:
            r.content

        return r
```
([sessions.py#L826-L829](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L826-L829))

`stream` was read out of the kwargs back at the top of `send` ([sessions.py#L774](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L774)), and Chapter 6 settled it at `False` — the Session default, untouched by the caller. So the body gets read now, inside the library, before the Response is ever handed back. The bare expression statement `r.content` looks like a no-op; it is the entire download.

## Draining the stream

`content` is a property. Its first test is `if self._content is False:` — the sentinel `Response.__init__` set ([models.py#L765-L768](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L765-L768)), meaning *not read yet*, distinct from a legitimately empty `b""` or a `None`. `_content_consumed` is False, `status_code` is 200 and `raw` is not None, so it falls to the real work:

```python
                self._content = b"".join(self.iter_content(CONTENT_CHUNK_SIZE)) or b""
```
([models.py#L1034-L1051](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1034-L1051))

`CONTENT_CHUNK_SIZE` is `10 * 1024` ([models.py#L104](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L104)), which is why the trace records the call as `iter_content(chunk_size=10240, decode_unicode=False)`.

`iter_content` is mostly guards. It raises `StreamConsumedError` if a stream has already been drained ([models.py#L958-L959](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L958-L959)) and `TypeError` for a non-integer chunk size ([models.py#L960-L965](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L960-L965)). Then it branches: for an already-consumed response it replays the cached bytes through `iter_slices` ([models.py#L967-L970](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L967-L970), [utils.py#L621-L630](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L621-L630)); here it is not, so it returns the `generate()` generator unstarted ([models.py#L971-L977](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L971-L977)). `decode_unicode` is False, so the decoding wrapper is skipped and the chunks stay bytes. The trace shows exactly that: a `<generator object ... generate>`, returned without running.

`b"".join` is what runs it. The trace records two entries into `generate`: the first yields `b'{"authenticated": true, "user": "user"}'`, the second finds the stream exhausted and falls through to the last line of the function.

```python
            if hasattr(self.raw, "stream"):
                try:
                    yield from self.raw.stream(chunk_size, decode_content=True)
```
([models.py#L935-L956](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L935-L956))

Note `decode_content=True` here, against the `decode_content=False` the adapter passed to `urlopen` in Chapter 7 ([adapters.py#L696-L708](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L696-L708)). That is deliberate: content decoding — gzip, deflate, brotli — is deferred from transport time to read time, so `raw` stays a genuinely raw stream for anyone who wants it, while `content` and `iter_content` give you decompressed bytes. Our server sent no `Content-Encoding`, so the 39 bytes arrive as they were written.

The `try` around that `yield from` is the second half of Chapter 7's exception-translation contract, and it covers the half that happens *after* a status line has already been seen: `ProtocolError` becomes `ChunkedEncodingError`, `DecodeError` becomes `ContentDecodingError`, `ReadTimeoutError` becomes `ConnectionError`, urllib3's `SSLError` becomes `requests.exceptions.SSLError` ([models.py#L940-L947](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L940-L947)).

On the way out, `generate` sets `self._content_consumed = True` ([models.py#L956](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L956)), and `content` sets it again and caches the joined bytes ([models.py#L1048](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1048)). The comment beside it states the ownership rule plainly: *don't need to release the connection; that's been handled by urllib3 since we exhausted the data* ([models.py#L1049-L1050](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1049-L1050)). Draining the stream is what returns the socket to the pool. `Response.close()` exists for the other case — it closes `raw` only when the content was *not* consumed, then calls `release_conn` ([models.py#L1173-L1184](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1173-L1184)) — and nothing in this run needed it.

> **For the owner:** With the default `stream=False`, Requests reads the whole body into memory before returning, which bounds nothing by size but guarantees the connection is released. If any caller passes `stream=True`, require that they consume the body or use the response as a context manager; an unread streamed response holds a pooled connection open, and transport errors can still surface from `iter_content` long after a `200` was observed.

## Closing up

`r.content` returns, `Session.send` returns `<Response [200]>`, `Session.request` returns it unchanged ([sessions.py#L651-L653](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L651-L653)), and control reaches the end of the `with` block that Chapter 1 opened:

```python
    with sessions.Session() as session:
        return session.request(method=method, url=url, **kwargs)
```
([api.py#L70-L71](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/api.py#L70-L71))

`Session.__exit__` calls `close()` ([sessions.py#L508-L509](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L508-L509)), which loops over the mounted adapters ([sessions.py#L883-L886](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L883-L886)) — the trace shows `HTTPAdapter.close` twice, one for `https://` and one for `http://`. Each clears its PoolManager and any ProxyManagers, which closes the pooled connections ([adapters.py#L555-L563](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L555-L563)). The socket that was handed back to the pool a moment ago is now simply gone. That is the trade the comment above the `with` block names outright: no leaked sockets and no `ResourceWarning`, at the price of no keep-alive between successive `requests.get` calls ([api.py#L67-L71](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/api.py#L67-L71)).

## What the caller sees

Back in the scenario, the Response is a plain object with cached bytes and no live resources.

`r.status_code` and `r.encoding` are attributes; they do not appear in the trace because nothing is computed. `r.headers["content-type"]` does appear: `CaseInsensitiveDict.__getitem__` lower-cases the key before looking it up, which is why the header the server spelled `Content-Type` answers to `content-type` ([structures.py#L64-L65](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/structures.py#L64-L65)). It returns `'application/json; charset=utf-8'`.

`r.text` touches `content` twice — once for the emptiness check, once to decode ([models.py#L1053-L1089](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1053-L1089)) — and the trace shows exactly two cached returns of the same bytes. Because `self.encoding` is `'utf-8'`, set from the charset parameter back in Chapter 8, the `apparent_encoding` fallback is skipped ([models.py#L1074-L1075](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1074-L1075)). The decode is `str(self.content, 'utf-8', errors="replace")`, wrapped in a `try` that falls back to a bare best-effort decode on `LookupError` or `TypeError` ([models.py#L1078-L1087](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1078-L1087)). Out comes `'{"authenticated": true, "user": "user"}'`.

> **For the owner:** `Response.text` never raises on bad bytes or an unknown charset — it substitutes replacement characters and moves on. When the server sends no charset, the encoding is a statistical guess from charset_normalizer or chardet ([models.py#L896-L904](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L896-L904)). Use `r.content` and decode explicitly anywhere the exact text matters.

`r.json()` is called twice in the scenario, and the trace shows it doing the same work both times — there is no cache ([models.py#L1091-L1124](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1091-L1124)). Its first test is `if not self.encoding and self.content and len(self.content) > 3`; `encoding` is `'utf-8'`, so the whole BOM-sniffing branch with `guess_json_utf` is skipped and it goes straight to `complexjson.loads(self.text)` ([models.py#L1119-L1120](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1119-L1120)) — which is why the trace nests `text` → `content` ×2 under each `json` call. A malformed body would come back as `requests.exceptions.JSONDecodeError`, Requests' own alias over the stdlib and simplejson errors ([models.py#L1121-L1124](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1121-L1124)). Here it returns `{'authenticated': True, 'user': 'user'}`.

And that is the end of the journey — with one thing conspicuously absent. Nowhere in these fifty lines of trace did anything inspect the status code. A 404 or a 500 would have travelled this identical path and produced an identical, perfectly parseable `Response`; `raise_for_status` is a method the caller must choose to call ([models.py#L1144-L1171](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L1144-L1171)), and `bool(r)` is no more than `status_code < 400` dressed up ([models.py#L837-L845](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L837-L845), [models.py#L861-L874](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L861-L874)).

> **For the owner:** Requests raises for transport failures, not for HTTP error statuses. Call `raise_for_status()` or check `status_code` explicitly in every code path that treats a response as success.

> **Leaves as:** `r.status_code == 200`, `r.headers['content-type'] == 'application/json; charset=utf-8'`, `r.encoding == 'utf-8'`, `r.text == '{"authenticated": true, "user": "user"}'`, `r.json() == {'authenticated': True, 'user': 'user'}` — a fully read, fully closed Response holding 39 cached bytes
