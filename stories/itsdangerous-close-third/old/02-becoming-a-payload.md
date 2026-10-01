# Chapter 2 · Becoming a Payload

> **Enters as:** `obj={'id': 5, 'name': 'itsdangerous'}`, `salt=None`

Now the dict arrives. It is an ordinary Python object — two keys, an int, a str — and the caller hands it to `dumps` with no salt argument, meaning "use whatever context this serializer was built for" ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L309-L320)).

The very first thing `dumps` does is turn the object into bytes: `payload = want_bytes(self.dump_payload(obj))` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L314)). Because of the mixin ordering established in chapter 1, `self.dump_payload` is not the base implementation — it is the URL-safe one ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L55-L69)), and its first act is to call `super().dump_payload(obj)` and get the plain bytes it will then dress up for a URL.

**Text first.** Inside `Serializer.dump_payload`, the dict meets `_CompactJSON.dumps` with `**self.serializer_kwargs` splatted in — empty here, but this is the seam where caller-supplied options change the bytes that will be signed ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L271-L276)). Out comes `'{"id":5,"name":"itsdangerous"}'` — thirty characters, no spaces after the commas or colons, because `_CompactJSON` sets `separators=(",", ":")` ([_json.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/_json.py#L14-L18)). Then `want_bytes` encodes it UTF-8 ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)), and `dump_payload` returns `b'{"id":5,"name":"itsdangerous"}'`. The contract here is worth naming: `dump_payload` always returns bytes, even when the inner serializer speaks text. Everything downstream — compression, base64, HMAC — works on bytes only.

**A compression attempt that is thrown away.** Back in the mixin, the payload is offered to zlib unconditionally:

```
compressed = zlib.compress(json)
if len(compressed) < (len(json) - 1):
```

([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L57-L63)). Thirty bytes of JSON with no repetition is not compressible; zlib's own framing makes the result longer, so the branch is not taken and `is_compressed` stays `False`. Note the `- 1`: the mixin only accepts compression if it saves at least two bytes, because keeping it costs one byte of marker. The trace shows no zlib call because `zlib.compress` is C code and not traced, but the outcome is visible in the result — the payload that comes out is the base64 of the *uncompressed* JSON.

Two things for an owner to file away here. First, compression runs on every dump, so you pay a little CPU for payloads that will never shrink; for the thousand-character string in the project's own tests it pays off handsomely. Second, and more interesting: compressing before signing means the *length* of the token depends on how compressible the plaintext is. That is an accepted property of this design, not an oversight — but if you ever put attacker-influenced data next to a secret in the same payload, that length is a side channel. Nothing in this scenario does that.

**Made URL-safe.** Finally `base64_encode` takes the JSON bytes ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25)). It calls `want_bytes` again (a no-op on bytes), runs `base64.urlsafe_b64encode`, and strips the trailing `=` padding. Out comes `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — forty characters drawn only from `A-Za-z0-9-_`. That alphabet is the whole point twice over: it survives a URL untouched, and it cannot contain a `.`, which is the character that will separate payload from signature in a moment.

Since `is_compressed` is `False`, the `b"." + base64d` marker is skipped ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L66-L67)). The payload leaves with no leading dot — and that absence is itself a message to the reader on the far side, who will check for exactly that byte before deciding whether to decompress.

The dict is gone. What travels on is forty bytes of base64, still fully readable by anyone who cares to decode it, and so far entirely unprotected.

> **Leaves as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — base64 of the compact JSON, no leading `.` marker
