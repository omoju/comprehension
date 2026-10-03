# Chapter 8 · Out to the caller, and closing a client that owns nothing

> **Enters as:** `<Response [200 OK]>` with `_content == b'Hello World!'`, headers `Content-Type: text/plain; charset=utf-8` and `Content-Length: 12`, `.request` set to `<Request('GET', 'http://testserver/')>`, inside a `Client` in state `OPENED`

The response is back in the caller's hands and the body is already bytes in memory. What remains is four attribute accesses, two assertions, and the exit of the `with` block. None of it touches the application again; all of it is the client answering questions about what it already has.

## repr, and a reason phrase that was never on the wire

`print(response)` calls `__repr__` ([_models.py#L859-L860](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L859-L860)):

```
return f"<Response [{self.status_code} {self.reason_phrase}]>"
```

`reason_phrase` looks for `self.extensions["reason_phrase"]`, finds nothing — the WSGI transport never set it — and falls through to `codes.get_reason_phrase(200)` ([_models.py#L619-L626](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L619-L626)), which looks `200` up in the enum and returns `'OK'` ([_status_codes.py#L38-L43](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_status_codes.py#L38-L43)). The result is `'<Response [200 OK]>'`. The application did send `"200 OK"` as its status string, but the transport parsed only the integer out of it ([wsgi.py#L143](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/wsgi.py#L143)); the phrase you see is reconstructed from a table. For an unknown status code `get_reason_phrase` returns the empty string rather than raising.

## The URL, unparsed back to a string

`response.request.url` goes through the `request` property — which would raise `RuntimeError` if `_request` were `None`, but chapter 6 set it ([_models.py#L595-L604](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L595-L604)) — and then `URL.__str__`, which delegates to the `ParseResult` ([_urls.py#L374-L375](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L374-L375), [_urlparse.py#L200-L210](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L200-L210)). The components reassemble to `'http://testserver/'` — the normalised form from chapter 2, not the `'/'` the caller typed. Note what `__str__` does *not* do: `__repr__` masks a password in the userinfo ([_urls.py#L377-L401](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L377-L401)), but `str()` emits it in full.

> **For the owner:** `str(url)` renders userinfo credentials verbatim, while `repr(url)` masks the password as `[secure]` ([_urls.py#L380-L382](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L380-L382)). The client's own INFO log line uses `%s` on the URL ([_client.py#L1025-L1032](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1025-L1032)), so credentials or tokens in a URL will land in your logs. Keep secrets out of URLs, or set the `httpx` logger above INFO.

## A header lookup that cannot fail on encoding

`response.headers["content-type"]` lowercases the key, encodes it with `self.encoding`, and collects every matching value ([_models.py#L284-L302](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L284-L302)):

```
if items:
    return ", ".join(items)
raise KeyError(key)
```

Two design points here. Duplicate headers are joined with `", "` per RFC 7230 rather than one being dropped — if you need them separate, `get_list()` is the API ([_models.py#L252-L272](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L252-L272)). And an absent header raises `KeyError`; `.get()` is the non-raising form ([_models.py#L242-L250](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L242-L250)).

The `encoding` property it consults is a sniffer: try `ascii` across all raw keys and values, then `utf-8`, then fall back to `iso-8859-1` ([_models.py#L166-L189](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L166-L189)). The comment is explicit about why the last one is there: ISO-8859-1 covers all 256 byte values, so it "will never raise decode errors." Header access is total — a server cannot make it throw a `UnicodeDecodeError`. Here everything is ASCII, and the trace records `'ascii'`. The answer is `'text/plain; charset=utf-8'`.

## Bytes to text: charset, validation, and a decoder that never raises

`response.text` is the one access that does real work ([_models.py#L641-L650](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L641-L650)). It reads `self.content` — `b'Hello World!'`, available because chapter 7 buffered it — then asks for an encoding.

`Response.encoding` implements a three-step priority ([_models.py#L652-L672](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L652-L672)):

1. `charset_encoding`, parsed out of Content-Type by stuffing the header into an `email.message.Message` and calling `get_content_charset` ([_models.py#L85-L90](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L85-L90), [_models.py#L688-L697](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L688-L697)). That returns `'utf-8'`.
2. If that is `None` *or* `_is_known_encoding` says `codecs.lookup` doesn't recognise it ([_models.py#L56-L64](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L56-L64)), fall back to `default_encoding` — the `'utf-8'` string the client attached in chapter 6, or, if it were a callable, a charset-autodetection function run over `_content`.
3. Failing everything, `"utf-8"`.

So a server that advertises a nonsense charset cannot break text decoding; the bogus value is discarded and the default takes over. Here `_is_known_encoding('utf-8')` returns `True` and `self._encoding` is set to `'utf-8'`.

Then a `TextDecoder` is built — and the critical argument is in its constructor ([_decoders.py#L311-L315](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L311-L315)):

```
self.decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
```

`errors="replace"`. `.text` will never raise on malformed bytes; invalid sequences become U+FFFD. Twelve clean ASCII bytes decode to `'Hello World!'`, the flush returns `''`, and the joined result is cached in `_text`.

That cache is also a lock: `encoding`'s setter raises `ValueError` if `_text` already exists ([_models.py#L674-L686](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L674-L686)), so a single response can never report two different texts. The scenario's second `response.text` at the end of the trace returns the cached string without re-decoding.

> **For the owner:** `.text` silently substitutes replacement characters for undecodable bytes ([_decoders.py#L312](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_decoders.py#L312)) and guesses an encoding when the server omits or mis-states the charset ([_models.py#L664-L671](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L664-L671)). Use `.content` wherever byte-exactness matters, such as signature verification or binary payloads.

## The audit trail: the header that was actually sent

`response.request.headers["X-Custom"]` returns `'value'`. This is not the dictionary the caller passed to `get()`; it is the `Headers` object on the `Request` that `_send_single_request` handed to the transport, after the merge of chapter 3 and the `Host`-prepending rebuild of `Request._prepare` ([_models.py#L460](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L460)). The request object is the record of what went out, which is why checking it is the right way to confirm a merge behaved.

## Exiting the block

The `with` statement ends and `Client.__exit__` runs ([_client.py#L1293-L1304](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1293-L1304)):

```
self._state = ClientState.CLOSED
self._transport.__exit__(exc_type, exc_value, traceback)
for transport in self._mounts.values():
    if transport is not None:
        transport.__exit__(exc_type, exc_value, traceback)
```

The state flips to `CLOSED` unconditionally — before any cleanup, and regardless of whether the block exited by exception. From here `send()` raises `RuntimeError("Cannot send a request, as the client has been closed.")` ([_client.py#L900-L901](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L900-L901)) and `__enter__` refuses to reopen it ([_client.py#L1275-L1283](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1275-L1283)). A `Client` is single-lifecycle.

`_mounts` is empty, as chapter 1 established, so the loop does nothing. The transport's `__exit__` calls `close()` ([base.py#L18-L24](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/base.py#L18-L24)), and `WSGITransport` does not override it, so it lands on `BaseTransport.close`'s `pass` ([base.py#L61-L62](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_transports/base.py#L61-L62)). There is nothing to release: no socket, no file handle, no pool. This client owned a function.

That emptiness is specific to this scenario. With a real `HTTPTransport`, this same exit is what closes the connection pool ([_client.py#L1263-L1273](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1263-L1273)) — which is why the documented usage is the context-manager form.

> **For the owner:** A `Client` that is neither context-managed nor explicitly `.close()`d leaks keep-alive connections when it uses a real transport ([_client.py#L1270-L1273](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1270-L1273)). Require `with httpx.Client(...)` or a `try/finally` around `close()` in any long-lived service code you sign off on.

The response survives its client. Because the body was buffered into `_content` during the read, `response.text` and `response.content` keep answering after the close ([_models.py#L636-L650](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L636-L650)) — the final `response.text` in the trace is served from the `_text` cache. Had the caller used `client.stream(...)` and held an unread response past the block, the stream would be closed and `iter_raw` would raise `StreamClosed` ([_models.py#L941-L942](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L941-L942)).

The string `'Hello World!'` that the application returned as a one-element list has travelled through a byte stream, a chunker, an identity decoder, a `join`, and an incremental UTF-8 decoder, and come out the other side as exactly itself.

> **Leaves as:** `'<Response [200 OK]>'`, `'http://testserver/'`, `'text/plain; charset=utf-8'`, `'Hello World!'`; `request.headers['X-Custom'] == 'value'`; the client in state `ClientState.CLOSED` with the response still fully readable
