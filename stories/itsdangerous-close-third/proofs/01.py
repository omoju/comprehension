"""Chapter 1: constructing URLSafeSerializer("secret key", "auth")."""
from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.encoding import want_bytes
from itsdangerous.serializer import Serializer, is_text_serializer
from itsdangerous.signer import Signer, _make_keys_list, _lazy_sha1

# --- the pieces the constructor calls, with the trace's arguments ---
assert want_bytes("secret key", "utf-8", "strict") == b"secret key"
assert _make_keys_list("secret key") == [b"secret key"]
assert want_bytes("auth", "utf-8", "strict") == b"auth"
assert _CompactJSON.dumps({}) == "{}"          # the probe's throwaway call
assert is_text_serializer(_CompactJSON) is True

# --- the object the dict is about to be handed to ---
auth_s = URLSafeSerializer("secret key", "auth")

assert auth_s.secret_keys == [b"secret key"]
assert auth_s.secret_key == b"secret key"      # newest (last) key
assert auth_s.salt == b"auth"                  # bytes, not str
assert auth_s.serializer is _CompactJSON       # mixin's default, not stdlib json
assert Serializer.default_serializer is not _CompactJSON
assert auth_s.is_text_serializer is True
assert auth_s.signer is Signer
assert auth_s.signer_kwargs == {}
assert auth_s.serializer_kwargs == {}
assert auth_s.fallback_signers == []           # empty since 2.0
assert URLSafeSerializer.default_fallback_signers == []

# No crypto happened yet: the digest default is still the lazy shim.
assert Signer.default_digest_method is _lazy_sha1
assert Signer.default_key_derivation == "django-concat"

# Default salt, had the caller omitted it.
assert URLSafeSerializer("secret key").salt == b"itsdangerous"
# A list of keys would have been kept in order, oldest to newest.
assert URLSafeSerializer(["old", "new"], "auth").secret_keys == [b"old", b"new"]
