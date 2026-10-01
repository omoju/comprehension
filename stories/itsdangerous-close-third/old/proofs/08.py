"""Chapter 8: the verified payload becomes a dict again. Run from the repo root
with PYTHONPATH=src."""

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_encode
from itsdangerous.exc import BadData, BadPayload, BadSignature
from itsdangerous.serializer import Serializer

# --- the world from chapter 1, and the token from chapters 2-4 ---------------
auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}
token = auth_s.dumps(user)
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# --- chapters 5-7: the verified bytes this chapter starts from ---------------
payload = auth_s.make_signer(b"auth").unsign(token)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# --- chapter 8, trace lines 113-117: no compression marker, base64 decode ----
assert not payload.startswith(b".")  # dump_payload discarded the zlib version
from itsdangerous.encoding import base64_decode

assert base64_decode(payload) == b'{"id":5,"name":"itsdangerous"}'

# --- trace lines 118-122: is_text_serializer=True -> decode, then JSON -------
assert auth_s.is_text_serializer is True
assert Serializer.load_payload(auth_s, b'{"id":5,"name":"itsdangerous"}') == user

# --- trace line 113 -> 123: the mixin's load_payload, end to end -------------
assert auth_s.load_payload(payload) == user

# --- trace line 68 -> 123: what the caller actually sees --------------------
data = auth_s.loads(token)
assert data == user
assert data["name"] == "itsdangerous"

# --- the compression marker is the whole contract ---------------------------
long_value = "a" * 1000
long_token = auth_s.dumps(long_value)
long_payload = long_token.rsplit(".", 1)[0].encode()  # hand fix: the marker dot comes first, so split at the last dot
assert long_payload.startswith(b".")  # this one *was* worth compressing
assert auth_s.loads(long_token) == long_value

# --- failure modes: BadPayload, with the original error kept ----------------
try:
    auth_s.load_payload(b"." + base64_encode(b"not zlib data at all"))
except BadPayload as e:
    assert "zlib decompress" in e.message
    assert e.original_error is not None
else:
    raise AssertionError("expected BadPayload from the zlib guard")

try:
    Serializer.load_payload(auth_s, b"this is not json")
except BadPayload as e:
    assert e.original_error is not None
else:
    raise AssertionError("expected BadPayload from the JSON guard")

# BadPayload is BadData but NOT BadSignature, so it escapes the retry loop in
# Serializer.loads instead of causing the next signer to be tried.
assert issubclass(BadPayload, BadData)
assert not issubclass(BadPayload, BadSignature)

# --- the mixin accepts `serializer=` and then does not forward it -----------
class Boom:
    @staticmethod
    def dumps(obj, **kw):
        return "{}"

    @staticmethod
    def loads(payload):
        raise ValueError("this serializer should never be consulted")


# If `serializer` were forwarded to Serializer.load_payload, Boom.loads would
# run and the call would raise BadPayload. It returns the dict instead.
assert auth_s.load_payload(payload, serializer=Boom) == user

print("chapter 8 verified:", data)
