"""Chapter 8: verified bytes -> dict, and the guarantees around it."""
import json
import zlib

from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.encoding import base64_decode
from itsdangerous.exc import BadData, BadPayload, BadSignature

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}
token = auth_s.dumps(user)
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# The bytes as they enter this chapter, exactly as unsign returned them.
payload = auth_s.make_signer().unsign(token)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# No compression marker: dump_payload found zlib no shorter and prefixed nothing.
assert not payload.startswith(b".")
assert len(zlib.compress(b'{"id":5,"name":"itsdangerous"}')) >= len(
    b'{"id":5,"name":"itsdangerous"}'
) - 1

# base64_decode gives back the compact JSON text from chapter 2.
assert base64_decode(payload) == b'{"id":5,"name":"itsdangerous"}'

# is_text_serializer was True, so load_payload decodes to str before loads.
assert auth_s.is_text_serializer is True
assert auth_s.serializer is _CompactJSON
assert _CompactJSON.loads('{"id":5,"name":"itsdangerous"}') == user

# The mixin's load_payload, end to end, and then the full loads().
assert auth_s.load_payload(payload) == user
data = auth_s.loads(token)
assert data == user
assert data["name"] == "itsdangerous"

# Failure mode: junk that decodes as base64 but is not JSON becomes BadPayload,
# with the original error kept, and BadPayload is BadData but NOT BadSignature.
bad = auth_s.make_signer().sign(b"bm90LWpzb24")  # base64 of b"not-json"
try:
    auth_s.loads(bad)
except BadPayload as e:
    assert isinstance(e, BadData)
    assert not isinstance(e, BadSignature)
    assert e.original_error is not None
else:
    raise AssertionError("expected BadPayload to escape the loads loop")

# What is NOT promised: no confidentiality -- anyone can read the payload.
assert json.loads(base64_decode(token.split(".")[0])) == user
