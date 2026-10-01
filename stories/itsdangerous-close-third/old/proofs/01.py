"""Chapter 1: constructing URLSafeSerializer("secret key", "auth")."""
import json

from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.serializer import Serializer
from itsdangerous.signer import Signer

auth_s = URLSafeSerializer("secret key", "auth")

# _make_keys_list + want_bytes: a single str key becomes a one-element byte list.
assert auth_s.secret_keys == [b"secret key"]
assert auth_s.secret_key == b"secret key"

# The salt is encoded to bytes and stored as-is; it is not secret.
assert auth_s.salt == b"auth"

# The URL-safe mixin replaces stdlib json with _CompactJSON.
assert auth_s.serializer is _CompactJSON
assert Serializer.default_serializer is json
assert URLSafeSerializer.default_serializer is _CompactJSON

# is_text_serializer probes with a real dumps({}) call and caches the answer.
assert _CompactJSON.dumps({}) == "{}"
assert auth_s.is_text_serializer is True

# The signer class is chosen but not instantiated; no kwargs were given.
assert auth_s.signer is Signer
assert auth_s.signer_kwargs == {}

# Fallbacks default to the (empty, since 2.0) class list, copied not shared.
assert URLSafeSerializer.default_fallback_signers == []
assert auth_s.fallback_signers == []
assert auth_s.fallback_signers is not URLSafeSerializer.default_fallback_signers

assert auth_s.serializer_kwargs == {}
