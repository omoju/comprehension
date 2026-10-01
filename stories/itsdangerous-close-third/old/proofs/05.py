"""Chapter 5: loads() normalises the token and assembles exactly one candidate signer."""
from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import want_bytes
from itsdangerous.signer import Signer

auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})

# The data as it enters this chapter's span (trace line 68).
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# want_bytes(s=..., encoding='utf-8', errors='strict') -> the same 68 chars as bytes
# (trace lines 69-70).
normalised = want_bytes(token)
assert normalised == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
assert isinstance(normalised, bytes)

# The empty default fallback list is why the jury has one member.
assert auth_s.fallback_signers == []
assert URLSafeSerializer.default_fallback_signers == []

# iter_unsigners(None) yields exactly one signer (trace lines 71-86).
signers = list(auth_s.iter_unsigners(None))
assert len(signers) == 1
signer = signers[0]
assert type(signer) is Signer

# salt=None was replaced by the serializer's own salt before make_signer was called
# (trace line 72 shows make_signer(salt=b'auth')).
assert auth_s.salt == b"auth"
assert signer.salt == b"auth"
assert signer.secret_keys == [b"secret key"]
assert signer.sep == b"."

# A fresh Signer object each time: no shared per-message state.
assert list(auth_s.iter_unsigners(None))[0] is not signer

# The loop only retries on BadSignature; BadPayload is not caught by it.
from itsdangerous.exc import BadPayload, BadSignature
assert not issubclass(BadPayload, BadSignature)
