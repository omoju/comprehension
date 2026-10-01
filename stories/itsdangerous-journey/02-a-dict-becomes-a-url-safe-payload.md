# Chapter 2 · A Dict Becomes a URL-Safe Payload

> **I arrive as:** `obj={'id': 5, 'name': 'itsdangerous'}`

I am a dictionary — a Python object with a small integer in it and a string. Nothing about me can be put in a URL. `Serializer.dumps` has just been entered, and its very first act is [`payload = want_bytes(self.dump_payload(obj))`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L314-L314). That `self.dump_payload` is not the one written three lines below it in `serializer.py`. Because I live on a `URLSafeSerializer`, and `URLSafeSerializerMixin` [comes first in the MRO](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L72-L76), the call lands in [the mixin's `dump_payload`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L55-L69). The trace shows exactly that ordering: `URLSafeSerializerMixin.dump_payload` on the outside, `Serializer.dump_payload` called from within it.

## First, become bytes

The mixin's first line is [`json = super().dump_payload(obj)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L56-L56), which is [the base implementation](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L271-L276) — a single expression: `want_bytes(self.serializer.dumps(obj, **self.serializer_kwargs))`.

`self.serializer` is the `_CompactJSON` chosen in chapter 1, and `self.serializer_kwargs` is the empty dict, so this is a plain `dumps(obj)`. [`_CompactJSON.dumps`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/_json.py#L14-L18) sets `ensure_ascii=False` and `separators=(",", ":")` and hands off to the stdlib. I come out as the string `'{"id":5,"name":"itsdangerous"}'` — 30 characters, no spaces.

Two things about that string are worth an owner's attention. It preserves my insertion order, because nothing here passes `sort_keys`; the same dict built in a different key order would serialize differently and therefore sign differently. And it is *the* canonical form of me from here on — the signature will cover bytes derived from this string, never my original dict.

Then [`want_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17) UTF-8 encodes it to `b'{"id":5,"name":"itsdangerous"}'`. This is the convergence point the docstring promises: *"The return value is always bytes. If the internal serializer returns text, the value will be encoded as UTF-8."* A `pickle`-backed serializer would have handed back bytes already and `want_bytes` would have passed them through untouched. Either way, everything downstream — compression, base64, HMAC — only ever sees bytes.

## Then, the compression gamble

Back in the mixin, three lines decide whether I get squeezed:

```
is_compressed = False
compressed = zlib.compress(json)
if len(compressed) < (len(json) - 1):
```

Note that [`zlib.compress` is called unconditionally](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L57-L58), before anyone knows whether it will help. That is a real cost paid on every single `dumps`, proportional to payload size — for a 30-byte user record it is invisible, for a fat session blob it is not. The design trades a guaranteed small CPU cost for a possible large size win, which is a defensible call for a library whose output lives in cookies and URLs, but it is a call, and it is not configurable.

The [comparison](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L60-L62) is `len(compressed) < len(json) - 1`, not `< len(json)`. The `- 1` is not a fudge factor: compression costs one extra byte in the final token, the marker dot that gets prepended below. So the rule is "only compress if it wins by at least the price of the flag."

For me it does not win. zlib's header and checksum alone are more than my 30 bytes can repay, and the compressed form is *longer* than the original. So the branch is not taken, `is_compressed` stays `False`, and `json` remains the raw UTF-8 JSON. The trace bears this out: no `zlib` frames leading to a changed value, and `base64_encode` is called on `b'{"id":5,"name":"itsdangerous"}'` — the same bytes that came out of `Serializer.dump_payload`.

Had compression won — the library's own tests exercise this with a 1000-character string — `json` would have been replaced by the compressed bytes and, after encoding, [a literal `b"."` would have been prepended](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L66-L67) as the marker. That is the only record that compression happened. There is no length field, no version byte, no header: one dot at the front, or nothing.

> Which raises the obvious question, and I do not yet know the answer: nothing marks *me* as uncompressed. How will the reader on the other side know not to try `zlib.decompress`?

One thing worth flagging as inference rather than something the code states: because compression runs before signing and the token's length is visible to anyone holding it, the length of a token leaks how compressible its payload was. The library is not encrypting anything — the payload is about to be plainly readable anyway — so this leaks nothing new here. It would matter if someone layered encryption on top of these tokens.

## Finally, become URL-safe

[`base64d = base64_encode(json)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L64-L64) calls [`base64_encode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25), which runs `want_bytes` once more (a no-op for me, already bytes — the trace shows it returning its input unchanged), then `base64.urlsafe_b64encode(string).rstrip(b"=")`.

Two choices, both about where I am going to live. `urlsafe_b64encode` uses `-` and `_` instead of `+` and `/`, so I survive a query string without percent-encoding. And `rstrip(b"=")` drops the padding, because `=` is noise in a URL and the decoder can reconstruct it arithmetically. For me the stripping did nothing at all: 30 bytes is divisible by 3, so the encoding came out to exactly 40 characters with no padding to remove. It would have mattered for a 31-byte payload.

I emerge as `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, and since `is_compressed` is `False` no dot is prepended — I go back to `dumps` as-is.

And here is the fact an owner should carry away from this chapter, because it is the single most common misunderstanding about this library: **I am encoded, not encrypted.** Base64 is a transcription, not a secret. Anyone who receives this token can run the reverse of these steps and read `{"id":5,"name":"itsdangerous"}` without the key. The guarantee ItsDangerous is building is *integrity* — that nobody can change the 5 to a 1 undetected — and nothing else. A user id and a display name are fine to ship this way. A password reset secret, an internal role flag you'd rather not disclose, an email address you promised not to expose in a URL — those are not fine, and no amount of correct signing makes them fine.

Back in `dumps`, [`want_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L314-L314) is applied to me one more time — belt and braces, since `dump_payload` already guarantees bytes — and returns me unchanged. I am now a payload waiting for a signature.

> **I leave as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — base64url of the compact JSON, uncompressed, no leading marker dot
