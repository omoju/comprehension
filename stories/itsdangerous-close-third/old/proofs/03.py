"""Chapter 3: the payload is re-checked by want_bytes, then make_signer builds
a Signer configured exactly as the trace records. Run with PYTHONPATH=src."""

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import _base64_alphabet, want_bytes
from itsdangerous.signer import HMACAlgorithm, Signer, _lazy_sha1

auth_s = URLSafeSerializer("secret key", "auth")
user = {"id": 5, "name": "itsdangerous"}

# --- trace line 29-30: want_bytes on an already-bytes payload is a no-op ---
payload = auth_s.dump_payload(user)
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert want_bytes(payload) == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# --- trace line 31-44: make_signer(None) substitutes the serializer's salt ---
signer = auth_s.make_signer(None)
assert isinstance(signer, Signer)
assert signer.salt == b"auth"

# the whole key list is handed over, re-normalised to bytes
assert auth_s.secret_keys == [b"secret key"]
assert signer.secret_keys == [b"secret key"]

# defaults filled in by Signer.__init__
assert signer.sep == b"."
assert signer.key_derivation == "django-concat"
assert signer.digest_method is _lazy_sha1
assert isinstance(signer.algorithm, HMACAlgorithm)
assert signer.algorithm.digest_method is _lazy_sha1

# nothing has been signed yet: the payload is unchanged
assert payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# a fresh Signer per call, holding no per-message state
assert auth_s.make_signer(None) is not signer

# the road not taken: a separator inside the base64 alphabet is rejected eagerly
assert b"." not in _base64_alphabet
assert b"-" in _base64_alphabet
try:
    Signer("secret key", salt="auth", sep="-")
except ValueError as e:
    assert "separator cannot be used" in str(e)
else:
    raise AssertionError("expected ValueError for a base64-alphabet separator")

# the road not taken: a bad key_derivation is NOT caught at construction
late = Signer("secret key", salt="auth", key_derivation="djangoconcat")
assert late.key_derivation == "djangoconcat"
try:
    late.derive_key()
except TypeError as e:
    assert "Unknown key derivation method" in str(e)
else:
    raise AssertionError("expected TypeError from derive_key")
