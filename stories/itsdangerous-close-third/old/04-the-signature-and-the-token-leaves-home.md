# Chapter 4 · The Signature, and the Token Leaves Home

> **Enters as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, handed to `Signer.sign`

The payload crosses into `sign`, and the first thing that happens to it is `want_bytes` again — the third time in this call chain ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L222-L225)). It is already bytes and comes back unchanged. `Signer` is a public class in its own right; it cannot assume a `Serializer` prepared its input.

`sign` is three tokens of logic: `value + self.sep + self.get_signature(value)`. Everything interesting is in that middle call.

## Deriving the key

`get_signature` normalises the value once more and then asks for a key ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L215-L220)). The trace shows `derive_key(secret_key=None)` — no key named, so the default branch fires:

```python
if secret_key is None:
    secret_key = self.secret_keys[-1]
```

([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L195-L198)). **There is the answer to the question chapter 3 left open.** The signer was handed the entire key list, but signing uses exactly one: the *last* entry, the newest. Verification, as we will see on the return trip, tries all of them. That asymmetry — sign with the newest, accept any — is the entire mechanism of key rotation. Rotate a new key onto the end of the list and old tokens keep working until you drop the old key off the front.

Here the list has one element, so `self.secret_keys[-1]` is `b'secret key'`.

The `key_derivation` is `'django-concat'`, so the second branch runs:

```python
return t.cast(bytes, self.digest_method(self.salt + b"signer" + secret_key).digest())
```

([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L202-L205)). The trace shows exactly what gets hashed: `_lazy_sha1(string=b'authsignersecret key')` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L40-L45)). Salt, a literal `b"signer"` separator, secret key — concatenated and hashed once. The digest is `b'\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8'`.

Two things to take from that byte string, reader.

**The salt's whole job is visible here.** Back in chapter 1 `'auth'` was turned into `b'auth'` and filed away; this is where it enters the cryptography, as a literal prefix on the hashed material. That is why two serializers sharing a secret key but differing in salt produce mutually unreadable tokens — the derived keys differ, so the HMACs differ. It is also why the salt does not need to be secret: it separates contexts, it does not protect them. The docs' activation-link-versus-upgrade-link example is exactly this ([concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L56-L92)).

**This is not a KDF.** One pass of SHA-1 over concatenated bytes is not stretching, not salting in the password sense, not iterated. The docstring says so plainly: *"Key derivation is not intended to be used as a security method to make a complex key out of a short password. Instead you should use large random secret keys"* ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L185-L188)). A weak `secret_key` stays weak. `"secret key"` — the README's string, and ours — is a demo value, and a reviewer signing off on a deployment should be asking where the real one comes from. The alternative derivations (`concat`, `hmac`, `none`) are all in the same method ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L200-L213)); none of them stretch either.

## Computing the MAC

The derived key and the payload go to `HMACAlgorithm.get_signature`, which is two lines ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L62-L64)):

```python
mac = hmac.new(key, msg=value, digestmod=self.digest_method)
return mac.digest()
```

The two `_lazy_sha1(string=b'')` calls in the trace are `hmac.new` constructing its inner and outer hash objects; the digest method is a callable, so HMAC calls it twice to get fresh contexts. Out comes twenty raw bytes: `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`.

Note *what* was MACed: the base64 payload bytes, not the JSON, and not the compression decision separately. Whatever `dump_payload` produced — marker byte included, had there been one — is covered by the signature as a single opaque string. That is why the compression flag from chapter 2 cannot be flipped by an attacker.

On SHA-1: the digest method is used only as HMAC's intermediate hash, where collision resistance is not what carries the security. The project documents this explicitly rather than quietly defaulting ([concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L137-L154)), and `signer_kwargs={"digest_method": hashlib.sha512}` changes it if your policy demands it — at the cost of a longer token.

## Encoding and joining

Raw MAC bytes would be useless in a URL, so `get_signature` finishes with `base64_encode` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L220)), the same function that handled the payload in chapter 2: URL-safe alphabet, `=` padding stripped ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25)). Twenty bytes become twenty-seven characters: `b'6YP6T0BaO67XP--9UzTrmurXSmg'`. Every one of them is from the alphabet the separator check in chapter 3 forbade `sep` from being — that check and this line are the same guarantee seen from two sides.

Then the join:

> `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9' + b'.' + b'6YP6T0BaO67XP--9UzTrmurXSmg'`

The payload is still there, in the clear, readable by anyone who can run base64 in a browser console. **ItsDangerous signs; it does not encrypt.** If `{"id":5,"name":"itsdangerous"}` were a password reset nonce or a role claim, the holder of the token would be reading it. The guarantee is that they cannot *change* it.

## Back in `dumps`, and out the door

`Serializer.dumps` gets `rv` as bytes and consults the boolean it computed at construction ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L317-L320)):

```python
if self.is_text_serializer:
    return rv.decode("utf-8")
return rv
```

**And there is the other open question answered.** That throwaway `_CompactJSON.dumps({})` in chapter 1, which returned `'{}'` and was recorded as `is_text_serializer=True`, is what decides right here whether the caller gets `str` or `bytes`. Had the serializer been `pickle`, the probe would have returned bytes, the flag would be `False`, and this same line would hand back `b'...'` instead. The scenario's `assert isinstance(token, str)` passes because of a decision made before the dict ever arrived.

The trace's last line of this span is the return: `'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`. The scenario prints it and splits it on the first dot; `payload` is the base64 JSON, `signature` the MAC.

The dict is now a string of sixty-eight ASCII characters, safe in a URL, safe in a cookie, safe in an email. It goes out into a world that has no reason to be kind to it. What comes back may or may not be this.

> **Leaves as:** `'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'` — a `str` token handed to the caller
