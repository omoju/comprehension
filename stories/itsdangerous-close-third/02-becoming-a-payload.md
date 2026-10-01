# Chapter 2 · Becoming a Payload

> **Enters as:** `obj={'id': 5, 'name': 'itsdangerous'}`, `salt=None`

The dict arrives at `Serializer.dumps` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L309-L320)) as a live Python object: two keys, an int, a str. Nothing about it is portable yet. You cannot put a dict in a URL, and you certainly cannot sign one — HMAC takes bytes, not hash tables. So the very first thing `dumps` does, before any thought of signing, is send the object away to be written down: `self.dump_payload(obj)` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L314)).

Because this object is a `URLSafeSerializer`, `dump_payload` resolves to the mixin's version ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L55-L69)), and its first act is to delegate upward with `super().dump_payload(obj)` — so the dict travels one level further down before anything URL-specific touches it.

## Written down

In `Serializer.dump_payload` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L271-L276)) the dict finally stops being a dict. `self.serializer.dumps(obj, **self.serializer_kwargs)` — the `_CompactJSON` chosen back in chapter 1, with an empty kwargs dict — turns it into the text `'{"id":5,"name":"itsdangerous"}'`. Thirty characters, no spaces anywhere, because `_CompactJSON` forces `separators=(",", ":")` ([_json.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/_json.py#L14-L18)). Stdlib `json` would have written `{"id": 5, "name": "itsdangerous"}` and cost two more bytes in every URL that ever carries this token.

Then `want_bytes` encodes that text to UTF-8 ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)), and `b'{"id":5,"name":"itsdangerous"}'` goes back up to the mixin. This wrapper is why `dump_payload` can promise bytes regardless of what the inner serializer prefers: a text serializer's output gets encoded here, a binary one's passes through untouched.

> **For the owner:** `serializer_kwargs` is empty in this run, but note where it lands — straight into the call that produces the bytes that get signed. Anything a caller puts there changes the signed payload. That is fine for `sort_keys` or `skipkeys`; it is worth a second look if someone ever reaches for `default=` with a callable that can emit different output for equal inputs, because then two "identical" dumps stop producing identical tokens and any equality check on tokens quietly breaks.

## Weighed, and left as it was

Now the URL-safe part. The mixin compresses the payload unconditionally and *then* decides whether it was worth it ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L56-L63)):

```python
compressed = zlib.compress(json)
if len(compressed) < (len(json) - 1):
```

The trace does not record this call — `zlib.compress` is C, invisible to the tracer — but the outcome is legible in the result. Thirty bytes of JSON, most of it high-entropy field names appearing exactly once, does not compress: zlib's header and checksum alone cost more than the redundancy it can find. The condition is false, `is_compressed` stays `False`, and the dict's bytes continue unchanged.

The `- 1` in that comparison is not a rounding error. A compressed payload must be marked so the reader knows to decompress it, and the mark is one extra byte — a leading `.` added at the end ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L66-L67)). So compression only wins if it saves more than the flag costs. Had the payload been something like the `"a" * 1000` case the project tests, the branch would have gone the other way and this chapter's data would leave with a dot on its front.

> **For the owner:** Compression before signing is a length side-channel, and it is a deliberate trade. The token's length depends on how compressible the payload is, so anyone who can see tokens learns a little about their contents — and if an attacker can influence *part* of a payload that also contains a secret, repeated observations can leak whether their guess matched, the CRIME/BREACH pattern. For the intended use here — a user id and a display name, all of it the attacker's own data anyway — it costs nothing and saves URL length. For a payload that mixes attacker-controlled fields with a secret one, use the plain `Serializer` instead. This behaviour is not configurable; it is baked into the mixin.

## Made safe for a URL

The last step is `base64_encode` ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25)). It runs `want_bytes` again — harmless, the value is already bytes — and then `base64.urlsafe_b64encode(...).rstrip(b"=")`. Two things matter about that one line. *Urlsafe* means the alphabet is `A-Za-z0-9-_`: no `+`, no `/`, nothing a URL or a cookie will mangle. And `rstrip(b"=")` removes padding, which is both shorter and, less obviously, keeps the payload inside an alphabet that cannot collide with anything structural. Here the input is 30 bytes — exactly ten three-byte groups — so there was no padding to strip, and the output is exactly 40 characters:

`b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`

Crucially, none of those characters is a `.`. The dot is about to become the separator between payload and signature, and it will be the *last* dot that decides where the split happens. The payload's alphabet guarantees it contributes no dots at all; the compression marker, when present, contributes exactly one at the front, harmlessly to the left of the split.

Since `is_compressed` is `False`, no marker is prepended, and the bytes return to `dump_payload`'s caller unchanged. The dict `{"id": 5, "name": "itsdangerous"}` is now forty bytes of URL-safe base64 — readable by anyone who cares to decode it, and so far, vouched for by no one.

> **Leaves as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — base64, 40 bytes, no leading dot
