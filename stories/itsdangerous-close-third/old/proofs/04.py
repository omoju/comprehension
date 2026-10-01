import hashlib
import hmac

from itsdangerous import URLSafeSerializer

auth_s = URLSafeSerializer("secret key", "auth")

# Chapter 2's output, the value entering Signer.sign.
payload = auth_s.dump_payload({"id": 5, "name": "itsdangerous"})
assert payload == b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'

# Chapter 3's signer: whole key list, serializer's salt, dot separator.
signer = auth_s.make_signer(None)
assert signer.secret_keys == [b'secret key']
assert signer.salt == b'auth'
assert signer.sep == b'.'
assert signer.key_derivation == "django-concat"

# derive_key(None) uses the LAST key and hashes salt + b"signer" + key.
key = signer.derive_key()
assert key == b'\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8'
assert key == hashlib.sha1(b"authsignersecret key").digest()
assert key == signer.derive_key(signer.secret_keys[-1])

# The salt is a literal prefix, so a different salt derives a different key.
assert URLSafeSerializer("secret key", "upgrade").make_signer(None).derive_key() != key

# HMAC over the base64 payload with the derived key.
raw_sig = signer.algorithm.get_signature(key, payload)
assert raw_sig == b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'
assert raw_sig == hmac.new(key, msg=payload, digestmod=hashlib.sha1).digest()

# base64, padding stripped.
assert signer.get_signature(payload) == b'6YP6T0BaO67XP--9UzTrmurXSmg'

# value + sep + signature, still bytes.
assert signer.sign(payload) == (
    b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'
)

# dumps decodes to str because is_text_serializer was probed True at construction.
assert auth_s.is_text_serializer is True
token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
assert isinstance(token, str)
assert token == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg"

# The payload travels in the clear: signed, not encrypted.
import base64
head = token.partition(".")[0]
assert base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)) == (
    b'{"id":5,"name":"itsdangerous"}'
)
