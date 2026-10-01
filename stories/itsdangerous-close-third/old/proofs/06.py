"""Replays the scenario through Chapter 6: Signer.unsign splitting the token."""
import base64

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_decode, want_bytes
from itsdangerous.exc import BadSignature

auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# Chapter 5 left us with the token as bytes and one candidate signer.
s = want_bytes(token)
assert s == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
signers = list(auth_s.iter_unsigners(None))
assert len(signers) == 1
signer = signers[0]

# The separator check runs before any crypto; our token passes it.
assert signer.sep == b"."
assert signer.sep in s

# rsplit(sep, 1): the last dot wins.
value, sig = s.rsplit(signer.sep, 1)
assert value == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert sig == b"6YP6T0BaO67XP--9UzTrmurXSmg"

# base64_decode turns the presented signature back into the raw digest bytes.
raw_sig = base64_decode(sig)
assert raw_sig == b"\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh"
assert len(raw_sig) == 20  # SHA-1 digest

# unsign returns exactly the payload half.
assert signer.unsign(s) == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# Road not taken A: no separator -> BadSignature with payload=None, before any crypto.
try:
    signer.unsign(b"nodothere")
except BadSignature as e:
    assert str(e) == "No b'.' found in value"
    assert e.payload is None
else:
    raise AssertionError("expected BadSignature")

# Road not taken B: tampered value -> BadSignature carrying the unverified payload.
try:
    signer.unsign(b"eyJpZCI6Niwibm5tZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg")
except BadSignature as e:
    assert e.payload == b"eyJpZCI6Niwibm5tZSI6Iml0c2Rhbmdlcm91cyJ9"
    assert "does not match" in str(e)
else:
    raise AssertionError("expected BadSignature")

# base64_decode drops non-ascii with errors='ignore' and re-pads; it does not raise,
# and verify_signature simply reports False for a garbled signature.
assert base64_decode("6YP6T0BaO67XP--9UzTrmurXSmg\u00ff") == raw_sig
assert signer.verify_signature(value, b"!!!not-base64-at-all!!!") is False
assert signer.verify_signature(value, sig) is True

# A compressed payload keeps a leading b"." marker; rsplit still cuts correctly.
big = auth_s.dumps("a" * 1000)
bval, bsig = want_bytes(big).rsplit(b".", 1)
assert bval.startswith(b".")
assert bval.count(b".") == 1 and b"." not in bsig
assert auth_s.make_signer().unsign(want_bytes(big)) == bval
