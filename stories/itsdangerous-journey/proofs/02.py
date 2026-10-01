"""Chapter 2: {'id': 5, 'name': 'itsdangerous'} -> b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'."""

import base64
import zlib

from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.encoding import base64_encode
from itsdangerous.encoding import want_bytes
from itsdangerous.serializer import Serializer
from itsdangerous.url_safe import URLSafeSerializerMixin

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}

# The mixin's dump_payload wins the MRO, not Serializer's.
assert type(auth_s).dump_payload is URLSafeSerializerMixin.dump_payload
assert URLSafeSerializerMixin.dump_payload is not Serializer.dump_payload

# --- step 1: compact JSON, then bytes (Serializer.dump_payload)
assert _CompactJSON.dumps(user) == '{"id":5,"name":"itsdangerous"}'
inner = Serializer.dump_payload(auth_s, user)
assert inner == b'{"id":5,"name":"itsdangerous"}'
assert isinstance(inner, bytes)
assert len(inner) == 30
# want_bytes is what makes the text serializer's str into bytes.
assert want_bytes('{"id":5,"name":"itsdangerous"}') == inner

# --- step 2: compression is attempted and loses, by the len-1 rule.
compressed = zlib.compress(inner)
assert not (len(compressed) < (len(inner) - 1))

# --- step 3: urlsafe base64, padding stripped
base64d = base64_encode(inner)
assert base64d == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
# 30 bytes is a multiple of 3, so there was no padding to strip here...
assert base64.urlsafe_b64encode(inner) == base64d
# ...but the stripping is real for other lengths.
assert base64.urlsafe_b64encode(b"ab") == b"YWI="
assert base64_encode(b"ab") == b"YWI"

# --- the span's output
payload = auth_s.dump_payload(user)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
# uncompressed: no marker dot at the front
assert not payload.startswith(b".")

# Encoded, not encrypted: the payload is readable without any key.
assert base64.urlsafe_b64decode(payload) == b'{"id":5,"name":"itsdangerous"}'

# The road not taken: a compressible payload keeps the compressed form
# and gets the b"." marker prepended.
big = auth_s.dump_payload("a" * 1000)
assert big.startswith(b".")
assert len(big) < 100
assert zlib.decompress(base64.urlsafe_b64decode(big[1:] + b"=" * (-len(big[1:]) % 4))) == (
    b'"' + b"a" * 1000 + b'"'
)

print("chapter 2 ok")
