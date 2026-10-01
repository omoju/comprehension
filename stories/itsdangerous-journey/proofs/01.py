"""Chapter 1: the constructor turns two strings into a frozen configuration."""

import json

from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.encoding import want_bytes
from itsdangerous.serializer import is_text_serializer
from itsdangerous.serializer import Serializer
from itsdangerous.signer import _make_keys_list
from itsdangerous.signer import Signer

# --- the span: URLSafeSerializer("secret key", "auth") -> Serializer.__init__
auth_s = URLSafeSerializer("secret key", "auth")

# The single str key was widened into a one-element list of bytes.
assert auth_s.secret_keys == [b"secret key"]
assert _make_keys_list("secret key") == [b"secret key"]
# ...and the same code path handles rotation lists identically.
assert _make_keys_list(["old", "new"]) == [b"old", b"new"]

# want_bytes: str -> utf-8 bytes, bytes -> unchanged.
assert want_bytes("secret key") == b"secret key"
assert want_bytes(b"secret key") == b"secret key"
assert want_bytes("auth") == b"auth"

# The salt was encoded, not left as str, and not None.
assert auth_s.salt == b"auth"

# serializer=None fell back to the mixin's _CompactJSON, not stdlib json.
assert auth_s.serializer is _CompactJSON
assert Serializer.default_serializer is json
assert _CompactJSON.dumps({}) == "{}"
# compact separators, no ensure_ascii escaping
assert _CompactJSON.dumps({"id": 5, "name": "itsdangerous"}) == (
    '{"id":5,"name":"itsdangerous"}'
)

# is_text_serializer probes by actually calling dumps({}) and checking for str.
assert auth_s.is_text_serializer is True
assert is_text_serializer(_CompactJSON) is True


class _BytesSerializer:
    @staticmethod
    def dumps(obj, **kwargs):
        return json.dumps(obj).encode()

    @staticmethod
    def loads(payload):
        return json.loads(payload)


assert is_text_serializer(_BytesSerializer) is False

# signer is the *class*, not an instance; kwargs defaulted to empty dicts.
assert auth_s.signer is Signer
assert auth_s.signer_kwargs == {}
assert auth_s.serializer_kwargs == {}

# No implicit fallback signers, and the list is a copy of the class default.
assert auth_s.fallback_signers == []
assert Serializer.default_fallback_signers == []
assert auth_s.fallback_signers is not Serializer.default_fallback_signers

# salt=None takes the other branch: left as None for the signer to default.
assert URLSafeSerializer("secret key", None).salt is None

print("chapter 1 ok")
