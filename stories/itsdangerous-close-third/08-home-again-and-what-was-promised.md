# Chapter 8 · Home Again, and What Was Promised

> **Enters as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — verified bytes, handed from `Signer.unsign` straight into `self.load_payload(...)`

The bytes come back into [`Serializer.loads`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L339) and go nowhere except one place:

```python
return self.load_payload(signer.unsign(s))
```

The call is on `self`, and `self` is a `URLSafeSerializer`. Because `URLSafeSerializerMixin` comes first in that class's bases ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L72-L76)), the mixin's `load_payload` answers, not the base serializer's — which is exactly what chapter 2's `dump_payload` needs on the return leg, since the mixin is what base64-encoded these bytes in the first place.

## The dot that isn't there

The first thing the mixin does is look for a marker ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L30-L34)):

```python
decompress = False

if payload.startswith(b"."):
    payload = payload[1:]
    decompress = True
```

This payload starts with `e`, so `decompress` stays `False` and the bytes pass through untouched. That is the other half of a contract opened in chapter 2: `dump_payload` ran zlib, found the compressed form no shorter, kept the plain JSON, and therefore prefixed nothing ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L60-L68)). Had the payload been the thousand-`a` string the tests use, the token would have carried a leading `.` and this branch would have set the flag. One byte in the token is the whole signal — and note that it sits *inside* the signed value, so an attacker cannot flip it without breaking the HMAC.

The dot is also why chapter 6's split had to be `rsplit(sep, 1)`: a compressed token contains two dots, and only the last one separates payload from signature.

## Base64, again, in reverse

```
base64_decode(string=b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9')
  want_bytes(s=..., encoding='ascii', errors='ignore') → b'eyJpZCI6...'
  → b'{"id":5,"name":"itsdangerous"}'
```

[`base64_decode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L28-L38) re-adds the padding that `base64_encode` stripped — `b"=" * (-len(string) % 4)`, here forty characters so zero padding — and decodes. Out comes the thirty-byte JSON text that `_CompactJSON.dumps` produced in chapter 2, byte for byte.

The mixin wraps this in its own guard ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L36-L42)): a failure here becomes `BadPayload("Could not base64 decode the payload because of an exception", original_error=e)`. The decompression path, not taken, has the matching guard right below it ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L44-L51)). Both keep the underlying exception on `original_error` rather than discarding it.

> **For the owner:** On the path this run took, zlib only ever sees bytes whose signature has already been verified — `loads` calls `unsign` first and `load_payload` second. That ordering is the thing to preserve. The documented debugging recipe, catching `BadSignature` and calling `s.load_payload(e.payload)` yourself ([docs/serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L52-L64)), deliberately steps outside it: that payload is attacker-controlled and will be decompressed unverified. The docs flag the decode step as unsafe and explain why it is kept explicit. If you see `load_payload` or `loads_unsafe` in production code rather than in a debug tool, ask what stops a decompression bomb there.

## From text to a dict

The decoded JSON goes to `super().load_payload(json)` — the base [`Serializer.load_payload`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L243-L269). With `serializer=None` it uses the instance's own, and reads the boolean computed back in chapter 1 ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L252-L254)):

```python
if serializer is None:
    use_serializer = self.serializer
    is_text = self.is_text_serializer
```

`is_text_serializer` was `True` — that throwaway `dumps({})` probe returning `'{}'` — so the bytes are decoded to UTF-8 text before being handed over ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L260-L263)). The trace shows it: `_CompactJSON.loads(payload='{"id":5,"name":"itsdangerous"}')` receives a `str`, not bytes, and returns `{'id': 5, 'name': 'itsdangerous'}`. A binary serializer such as `pickle` would have taken the other line and received the raw bytes.

The entire call sits inside one `try` whose `except Exception` converts anything the inner serializer throws into `BadPayload` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L264-L269)). That is a deliberate narrowing of the blast radius: a serializer mismatch, a truncated JSON document, a `UnicodeDecodeError` — all surface as a `BadData` subclass the caller can catch, rather than as whatever exception type the third-party serializer happened to raise.

And `BadPayload` descends from `BadData`, *not* from `BadSignature` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L92-L99)). That matters for the loop in chapter 5: `loads` only catches `BadSignature` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L340-L341)). A payload that passed signature verification but cannot be parsed escapes immediately rather than quietly causing the next fallback signer to be tried. A correctly-signed token that doesn't parse is a bug or a serializer change, and it fails loudly.

The dict travels back out unchanged through the mixin, through `loads`, to the caller, where the scenario's `assert data == user` holds and `data["name"]` prints `itsdangerous`.

## What the round trip promises

The journey is over, so here is the contract in plain terms. The object returned by `loads` is the object that was passed to `dumps` by someone holding one of the keys in `secret_keys`, under this salt. That is it. Three things it explicitly does not promise:

**Confidentiality.** The payload rode across as readable base64 the entire way; anyone can decode it. The docs say so — the receiver "can see the data, but they can not modify it" ([docs/index.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/index.rst#L14-L20)).

**Freshness.** No timestamp was written and none was checked. A token stays valid until its key leaves the list. Expiry requires `URLSafeTimedSerializer`, whose signer stamps and verifies an age ([timed.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/timed.py#L45-L51), [timed.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/timed.py#L138-L146)).

**Single use.** Nothing here records that a token was seen. Replay is the caller's problem.

> **For the owner:** The default serializer is JSON ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L95), overridden to `_CompactJSON` by the URL-safe mixin at [url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L21)), and that is the single most load-bearing default in this file. JSON parsing of hostile bytes is dull; `pickle.loads` of hostile bytes is remote code execution. The library supports `serializer=pickle` and the docs warn against combining it with `loads_unsafe` ([docs/serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L58-L64)). Before signing off: confirm no `serializer=` argument in your call sites, and decide whether a token that never expires is acceptable for the thing you are putting in it. If it carries authorisation, you probably want the timed variant.

> **Leaves as:** `{'id': 5, 'name': 'itsdangerous'}` — the caller's dict, returned from `Serializer.loads`, equal to the one handed to `dumps`
