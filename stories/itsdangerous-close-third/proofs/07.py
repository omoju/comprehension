import hashlib
import hmac

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_decode
from itsdangerous.signer import Signer

auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# Chapter 5: loads() normalises and asks iter_unsigners for candidates.
signed = token.encode("utf-8")
signers = list(auth_s.iter_unsigners(None))
assert len(signers) == 1
signer = signers[0]
assert signer.secret_keys == [b"secret key"]
assert signer.salt == b"auth"

# Chapter 6: the split and the base64 decode of the presented signature.
value, sig = signed.rsplit(signer.sep, 1)
assert value == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert sig == b"6YP6T0BaO67XP--9UzTrmurXSmg"
raw_sig = base64_decode(sig)
assert raw_sig == b"\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh"

# Chapter 7, step 1: derive_key called with an explicit key (trace line 97).
key = signer.derive_key(b"secret key")
assert key == b"\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8"
# django-concat: sha1(salt + b"signer" + secret_key)
assert key == hashlib.sha1(b"authsignersecret key").digest()
# Same derived key as signing used, which defaults to secret_keys[-1].
assert signer.derive_key() == key

# Step 2: the HMAC is recomputed from scratch and matches (trace lines 104-109).
recomputed = signer.algorithm.get_signature(key, value)
assert recomputed == raw_sig
assert hmac.compare_digest(raw_sig, recomputed) is True
assert signer.algorithm.verify_signature(key, value, raw_sig) is True
assert signer.verify_signature(value, sig) is True

# Step 3: unsign returns the payload unchanged (trace line 112).
assert signer.unsign(signed) == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# The loop really does reject a payload that wasn't signed: flip id 5 -> 6.
forged = b"eyJpZCI6NiwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert signer.verify_signature(forged, sig) is False
assert signer.validate(forged + b"." + sig) is False

# reversed(secret_keys): an older key still validates after a newer one is added.
rotated = Signer([b"secret key", b"new key"], salt=b"auth")
assert rotated.secret_key == b"new key"
assert rotated.unsign(signed) == value
# ...and stops validating once that key is dropped from the list.
dropped = Signer([b"new key"], salt=b"auth")
assert dropped.validate(signed) is False
