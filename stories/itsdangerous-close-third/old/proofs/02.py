import zlib

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_encode, want_bytes
from itsdangerous.serializer import Serializer

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}

# The inner serializer produces compact JSON text (trace line 20).
json_text = auth_s.serializer.dumps(user, **auth_s.serializer_kwargs)
assert json_text == '{"id":5,"name":"itsdangerous"}', json_text

# Serializer.dump_payload (the super() call) returns those bytes (trace lines 18-23).
plain = Serializer.dump_payload(auth_s, user)
assert plain == b'{"id":5,"name":"itsdangerous"}', plain
assert want_bytes(json_text) == plain

# zlib was tried and rejected: it does not beat len(json) - 1, so no marker byte.
compressed = zlib.compress(plain)
assert not (len(compressed) < (len(plain) - 1)), (len(compressed), len(plain))

# base64_encode of the uncompressed JSON (trace lines 24-27).
assert base64_encode(plain) == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# What the mixin's dump_payload actually hands back (trace line 28).
payload = auth_s.dump_payload(user)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9", payload
assert not payload.startswith(b"."), "no compression marker was added"
assert isinstance(payload, bytes)
