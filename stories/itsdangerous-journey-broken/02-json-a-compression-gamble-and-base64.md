# Chapter 2 · JSON, a Compression Gamble, and Base64

> **I arrive as:** `{'id': 5, 'name': 'itsdangerous'}` — a plain Python dict, the user's identity, handed to `auth_s.dumps(user)`.

I am a dict. Nothing can sign a dict; HMAC eats bytes. So before anyone asks whether I am authentic, I have to become bytes — and that transformation is where the design decisions with the longest shadows get made, because whatever I look like here is what an attacker will hold in their hands.

## Handed down two levels

The method that receives me is [`Serializer.dumps`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L309-L320), and its very first line is [`payload = want_bytes(self.dump_payload(obj))`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L314-L314). That `self.dump_payload` resolves through the MRO to the URL-safe mixin's version, not the base one — [`URLSafeSerializerMixin.dump_payload`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L55-L69). Its first act is to call `super().dump_payload(obj)` and get the plain serialization out of the way.

That base method is one line: [`want_bytes(self.serializer.dumps(obj, **self.serializer_kwargs))`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L271-L276). My serializer is `_CompactJSON`, configured back in Chapter 1, and [its `dumps` sets `ensure_ascii=False` and `separators=(",", ":")` before delegating to stdlib `json`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/_json.py#L14-L18). So I come out as

```
'{"id":5,"name":"itsdangerous"}'
```

— 30 characters, where stdlib `json.dumps` would have given me `'{"id": 5, "name": "itsdangerous"}'` with its two cosmetic spaces. Three bytes saved matters when the destination is a cookie with a 4 KB budget. `serializer_kwargs` is `{}` here, but note it is passed straight through: it is the supported way to change JSON behaviour (`sort_keys`, `default`, `skipkeys`) without subclassing anything.

Then [`want_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17) UTF-8 encodes me, and I am `b'{"id":5,"name":"itsdangerous"}'`.

## The gamble

Back in the mixin, something slightly surprising happens: [I am compressed unconditionally, and only *then* is it decided whether to keep the result](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L56-L62).

```python
compressed = zlib.compress(json)

if len(compressed) < (len(json) - 1):
    json = compressed
    is_compressed = True
```

zlib always pays a fixed toll — a two-byte header and a four-byte Adler-32 checksum — before any of its savings begin. On 30 bytes of mostly-unique text there is nothing to save, so the compressed form comes out *longer* than I am. The test fails and I stay as I am, raw JSON.

The `- 1` in that comparison is not a fudge factor. It reserves exactly the one byte that a compressed payload will have to spend on its marker: [if compression wins, the result is prefixed with a literal `b"."`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L66-L67) so the reverse trip knows to decompress. Compression must therefore beat the alternative by at least two bytes to be worth taking. This is the road I don't travel — had I been the thousand-character string the library's own tests use, I would be carrying a leading dot right now.

It's worth an owner pausing on this branch for a second, because it is the one place in the whole flow where *my content* influences the *shape* of the output an attacker can see. A token's length tells you whether its payload compressed well. If a token ever carries a guessable value next to a secret one, that length is a side channel — the same family of problem as CRIME/BREACH. For an id and a username it is nothing. For a payload mixing attacker-controlled text with a secret token, it is worth thinking about.

## Base64, which is not encryption

Finally [`base64_encode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L64-L64) runs, and it is [`base64.urlsafe_b64encode` with the `=` padding stripped](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25). URL-safe means the alphabet uses `-` and `_` instead of `+` and `/`, so I survive being pasted into a query string, a path segment, or a cookie without escaping. The padding is dropped because it can be recomputed from my length, and `=` is another character that some contexts dislike.

My 30 bytes become 40 characters:

```
b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'
```

I want to be very direct about what this step is and is not, because it is the single most common misreading of this library. Base64 is a **reversible transform with no key**. Anyone holding this token can paste the left-hand side into a decoder and read `{"id":5,"name":"itsdangerous"}`. That answers the question left open in Chapter 1: the payload is public. ItsDangerous guarantees *integrity and authenticity* — that the data came back as it went out, or not at all — and it never promised *confidentiality*. Do not put anything in here you wouldn't email to the user, because effectively you are.

I am now bytes, encoded and dot-free, ready to be signed. Which raises the question I can't yet answer: if a compressed payload is just a dot followed by base64, what stops a client from *adding* a dot to a token and forcing the server to decompress data it chose?

> **I leave as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — 40 bytes of URL-safe base64, uncompressed, with no leading dot.

```python proof
import json as stdlib_json
import zlib

from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.encoding import base64_decode
from itsdangerous.serializer import Serializer

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}

# _CompactJSON strips the whitespace stdlib json would emit.
compact = _CompactJSON.dumps(user)
assert compact == '{"id":5,"name":"itsdangerous"}'
assert stdlib_json.dumps(user) == '{"id": 5, "name": "itsdangerous"}'

# Serializer.dump_payload is the base (non-URL-safe) step: JSON, then UTF-8 bytes.
raw = Serializer.dump_payload(auth_s, user)
assert raw == b'{"id":5,"name":"itsdangerous"}'
assert len(raw) == 30
assert auth_s.serializer_kwargs == {}

# The compression gamble: zlib is always tried, and here it loses.
compressed = zlib.compress(raw)
assert not (len(compressed) < (len(raw) - 1))
assert len(compressed) >= len(raw) - 1

# So the mixin keeps the raw JSON, base64url-encodes it, and adds no dot marker.
payload = auth_s.dump_payload(user)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert len(payload) == 40
assert not payload.startswith(b".")
assert b"=" not in payload  # padding stripped

# Base64 is reversible with no key: the payload is public, not secret.
assert base64_decode(payload) == raw
assert stdlib_json.loads(base64_decode(payload)) == user

# The road not taken: a highly compressible payload does win, and is marked
# with a leading dot that costs the one byte the `- 1` reserves.
big = "a" * 1000
big_raw = Serializer.dump_payload(auth_s, big)
assert len(zlib.compress(big_raw)) < len(big_raw) - 1
big_payload = auth_s.dump_payload(big)
assert big_payload.startswith(b".")
assert len(big_payload) < len(big_raw)
```
