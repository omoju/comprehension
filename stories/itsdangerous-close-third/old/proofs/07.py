import hashlib

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_decode
from itsdangerous.signer import Signer

# --- world of chapters 1-4: the token as it left home -----------------------
auth_s = URLSafeSerializer("secret key", "auth")
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# --- chapters 5-6: one signer, and the token cut in two ---------------------
signer = next(auth_s.iter_unsigners(None))
assert signer.secret_keys == [b"secret key"]
assert signer.salt == b"auth"

signed = token.encode("utf-8")
value, sig = signed.rsplit(signer.sep, 1)
assert value == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert sig == b"6YP6T0BaO67XP--9UzTrmurXSmg"

raw_sig = base64_decode(sig)
assert raw_sig == b"\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh"

# --- chapter 7: derive the key, recompute, compare --------------------------
# verify_signature calls derive_key with an explicit key (the want_bytes branch)
key = signer.derive_key(b"secret key")
assert key == b"\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8"
# django-concat: sha1(salt + b"signer" + secret_key)
assert key == hashlib.sha1(b"authsignersecret key").digest()
# ...and it is the same key signing used (derive_key(None) -> secret_keys[-1])
assert signer.derive_key() == key

# the HMAC is recomputed from scratch and equals the presented signature
assert signer.algorithm.get_signature(key, value) == raw_sig
assert signer.algorithm.verify_signature(key, value, raw_sig) is True
assert signer.verify_signature(value, sig) is True

# unsign returns the payload half alone
assert signer.unsign(signed) == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# --- the loop's reason for existing: reversed(secret_keys) ------------------
# an older key still verifies while it remains in the list, even though the
# newest key is the one that would sign
rotated = Signer(["secret key", "newer key"], salt=b"auth")
assert rotated.derive_key() == rotated.derive_key(b"newer key") != key
assert rotated.verify_signature(value, sig) is True
assert rotated.unsign(signed) == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# drop the old key and the same token is rejected
retired = Signer(["newer key"], salt=b"auth")
assert retired.verify_signature(value, sig) is False

# a different salt derives a different key, so the verdict flips
other_salt = Signer(["secret key"], salt=b"upgrade")
assert other_salt.derive_key(b"secret key") != key
assert other_salt.verify_signature(value, sig) is False

# a tampered payload fails against the very same signature
assert signer.verify_signature(b"eyJpZCI6NiwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9", sig) is False
