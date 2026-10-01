# hand fix: pytest isn't installed in the repo's environment; plain try/except instead
from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import _base64_alphabet, want_bytes
from itsdangerous.signer import _lazy_sha1, HMACAlgorithm, Signer

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}

# --- entering the span: the payload from chapter 2, passed through want_bytes ---
payload = auth_s.dump_payload(user)
assert payload == b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'
assert want_bytes(payload) == b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'

# --- make_signer(None) substitutes the serializer's own salt ---
assert auth_s.salt == b"auth"
signer = auth_s.make_signer(None)
assert isinstance(signer, Signer)
assert signer.salt == b"auth"

# ...and hands over the whole key list, plus empty signer_kwargs
assert auth_s.secret_keys == [b"secret key"]
assert auth_s.signer_kwargs == {}
assert signer.secret_keys == [b"secret key"]

# --- the separator check: b"." is not in the base64 alphabet, so it is allowed ---
assert signer.sep == b"."
assert b"." not in _base64_alphabet
try:
    Signer("secret key", salt="auth", sep="-")
    raise AssertionError("separator '-' should be refused")
except ValueError as e:
    assert "separator cannot be used" in str(e)

# --- defaults filled in from class attributes ---
assert signer.key_derivation == "django-concat"
assert Signer.default_key_derivation == "django-concat"
assert signer.digest_method is _lazy_sha1
assert isinstance(signer.algorithm, HMACAlgorithm)
assert signer.algorithm.digest_method is _lazy_sha1

# key_derivation is NOT validated here; it fails later, in derive_key
bad = Signer("secret key", salt="auth", key_derivation="hmc")
assert bad.key_derivation == "hmc"
try:
    bad.derive_key()
    raise AssertionError("key_derivation 'hmc' should be refused")
except TypeError as e:
    assert "Unknown key derivation method" in str(e)

# --- a fresh signer per call; nothing is cached on the serializer ---
assert auth_s.make_signer(None) is not signer

# --- leaving the span: the payload is untouched ---
assert payload == b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'
