from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import want_bytes
from itsdangerous.signer import Signer

# The world from chapter 1, the token from chapter 4.
auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
assert isinstance(token, str)

# loads() first normalises the str token back to bytes (trace line 69-70).
s = want_bytes(token)
assert s == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
assert isinstance(s, bytes)
# ASCII round trip is lossless.
assert s.decode("utf-8") == token

# iter_unsigners(None) substitutes the serializer's own salt and yields
# exactly one signer, because fallback_signers is empty (trace lines 71-86).
assert auth_s.fallback_signers == []
unsigners = list(auth_s.iter_unsigners(None))
assert len(unsigners) == 1

signer = unsigners[0]
assert type(signer) is Signer
assert signer.secret_keys == [b"secret key"]
assert signer.salt == b"auth"
assert signer.sep == b"."
assert signer.key_derivation == "django-concat"

# A fresh object each time, not the one that signed.
assert signer is not list(auth_s.iter_unsigners(None))[0]

# The salt used for verification is the one chosen at construction,
# which is why an explicit different salt would build a different signer.
assert list(auth_s.iter_unsigners("other"))[0].salt == b"other"

# loads() catches BadSignature per candidate; with none succeeding it
# re-raises the last one, and never returns a partial value.
from itsdangerous.exc import BadSignature

try:
    auth_s.loads(token, salt="other")
except BadSignature as err:
    # The rejected payload is attached, but only on the exception.
    assert err.payload == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
else:
    raise AssertionError("wrong salt must not verify")
