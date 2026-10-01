"""Chapter 6: Signer.unsign splits the token and decodes the signature.

Run from the repo root with PYTHONPATH=src.
"""

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_decode
from itsdangerous.encoding import want_bytes
from itsdangerous.exc import BadSignature

# --- world from chapters 1-4: the token exists and has left home -------------
auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# --- chapter 5 handed these bytes to the single candidate signer -------------
s = want_bytes(token)
assert s == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
signer = next(auth_s.iter_unsigners())
assert signer.secret_keys == [b"secret key"]
assert signer.salt == b"auth"
assert signer.sep == b"."

# --- unsign, step by step ----------------------------------------------------
# want_bytes on already-bytes input is the identity
assert want_bytes(s) is s

# the separator guard passes, so nothing is raised here
assert signer.sep in s

# the last dot wins
value, sig = s.rsplit(signer.sep, 1)
assert value == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert sig == b"6YP6T0BaO67XP--9UzTrmurXSmg"

# base64_decode restores the stripped padding and returns the raw digest
assert len(sig) == 27 and (-len(sig) % 4) == 1
raw_sig = base64_decode(sig)
assert raw_sig == b"\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh"
assert len(raw_sig) == 20  # SHA-1 digest length

# and the whole call returns exactly the payload half
assert signer.unsign(s) == value

# --- roads not taken ---------------------------------------------------------
# no separator: rejected before any crypto, with no payload attached
try:
    signer.unsign(value)
except BadSignature as e:
    assert str(e) == "No b'.' found in value"
    assert e.payload is None
else:
    raise AssertionError("expected BadSignature for a value with no separator")

# wrong signature: rejected, but the unverified payload IS attached
try:
    signer.unsign(value + b".AAAA")
except BadSignature as e:
    assert e.payload == value
    assert str(e) == "Signature b'AAAA' does not match"
else:
    raise AssertionError("expected BadSignature for a mismatched signature")

# unparseable signature text becomes a plain False, not a BadData escape
assert signer.verify_signature(value, b"!!!!") is False
