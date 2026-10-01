import zlib

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_encode
from itsdangerous.serializer import Serializer

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}

# The world from chapter 1 that this chapter depends on.
assert auth_s.serializer_kwargs == {}
assert auth_s.is_text_serializer is True

# _CompactJSON.dumps: compact separators, text out (trace lines 19-20).
json_text = auth_s.serializer.dumps(user, **auth_s.serializer_kwargs)
assert json_text == '{"id":5,"name":"itsdangerous"}'
assert len(json_text) == 30

# Serializer.dump_payload: same bytes, UTF-8 encoded (trace lines 18-23).
inner = Serializer.dump_payload(auth_s, user)
assert inner == b'{"id":5,"name":"itsdangerous"}'

# The compression branch that was weighed and not taken (url_safe.py L60).
compressed = zlib.compress(inner)
assert not (len(compressed) < (len(inner) - 1))

# base64_encode of the uncompressed JSON (trace lines 24-28).
payload = auth_s.dump_payload(user)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert payload == base64_encode(inner)

# No compression marker, no padding, no separator character.
assert not payload.startswith(b".")
assert b"." not in payload
assert b"=" not in payload
assert len(payload) == 40
