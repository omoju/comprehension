"""Replays the scenario through the end of Chapter 4: dict -> signed str token."""

import hashlib
import hmac as _hmac

from itsdangerous import URLSafeSerializer
from itsdangerous.encoding import base64_encode

auth_s = URLSafeSerializer("secret key", "auth")

# --- Chapter 3's exit state: the signer that does the work here. ---
signer = auth_s.make_signer(None)
assert signer.secret_keys == [b"secret key"]
assert signer.salt == b"auth"
assert signer.sep == b"."
assert signer.key_derivation == "django-concat"

payload = b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

# --- derive_key(): signing uses the NEWEST key only (secret_keys[-1]). ---
derived = signer.derive_key()
assert derived == b"\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8"
# and it is literally sha1(salt + b"signer" + secret_key):
assert derived == hashlib.sha1(b"authsignersecret key").digest()

# The salt is what separates contexts: same secret, different salt -> different key.
other = URLSafeSerializer("secret key", "upgrade").make_signer(None)
assert other.derive_key() != derived

# --- HMACAlgorithm.get_signature(): raw 20-byte digest over the BASE64 payload. ---
raw_sig = signer.algorithm.get_signature(derived, payload)
assert raw_sig == b"\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh"
assert raw_sig == _hmac.new(derived, msg=payload, digestmod=hashlib.sha1).digest()

# --- base64_encode(): 20 raw bytes -> 27 url-safe chars, padding stripped. ---
assert base64_encode(raw_sig) == b"6YP6T0BaO67XP--9UzTrmurXSmg"
assert signer.get_signature(payload) == b"6YP6T0BaO67XP--9UzTrmurXSmg"

# --- sign(): payload + sep + signature, payload carried through unchanged. ---
signed = signer.sign(payload)
assert signed == b"eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
assert signed.startswith(payload)
assert signed.count(b".") == 1

# --- dumps(): is_text_serializer is True, so the bytes are decoded to str. ---
assert auth_s.is_text_serializer is True
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert isinstance(token, str)
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"
assert token == signed.decode("utf-8")

# The guarantee is integrity, not confidentiality: the payload is readable.
import base64

assert base64.urlsafe_b64decode(payload + b"==") == b'{"id":5,"name":"itsdangerous"}'
