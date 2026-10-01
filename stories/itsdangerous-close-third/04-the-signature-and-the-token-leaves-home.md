# Chapter 4 · The Signature, and the Token Leaves Home

> **Enters as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, handed to `Signer.sign`

The payload is passed into `sign` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L222-L225)), which is three lines long and gives away the whole shape of the result:

```python
value = want_bytes(value)
return value + self.sep + self.get_signature(value)
```

The first line is the same no-op coercion as before — the trace shows `want_bytes` taking `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` and returning it unchanged ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)). It matters because `sign` is public: a caller may hand it text, and everything downstream is byte arithmetic.

The second line says something the owner should hear plainly: the payload is *concatenated*, not transformed. Whatever comes back, the readable base64 is still in it, unaltered, at the front.

## Deriving the key

`get_signature` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L215-L220)) coerces once more, then calls `self.derive_key()` with no argument.

Inside `derive_key` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L182-L213)), `secret_key is None`, so it takes the default branch: `secret_key = self.secret_keys[-1]` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L195-L196)). That is the answer to the question left open in chapter 3. The signer was handed a *list* of keys, but signing consults exactly one of them — the last, the newest. The list is for reading, not writing; it exists so that a rotation system can keep old keys around to verify old tokens while every new token is signed with the current one. Here the list has one element, so `b'secret key'` it is.

Then the derivation branch, chosen by the `"django-concat"` string stored at construction ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L202-L205)):

```python
return self.digest_method(self.salt + b"signer" + secret_key).digest()
```

The trace shows the concrete call: `_lazy_sha1(string=b'authsignersecret key')`. There it is — the salt, the literal word `signer`, and the secret, glued end to end and hashed. This is the first time in the whole run that a hash function has actually been touched, which is exactly what `_lazy_sha1` was deferring for ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L40-L45)). The digest comes back as twenty bytes: `b'\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8'`.

Two things follow from that one line. First, this is where the salt `'auth'` finally earns its keep: because it is a prefix of the hashed material, a serializer built with `salt="upgrade"` and the *same* secret key derives a completely different key and cannot verify this token. That is the context separation the docs describe, and it costs nothing secret — the salt can sit in source code.

Second, and less comfortable: this is a single unsalted-in-the-cryptographic-sense hash of a concatenation, not a key derivation function. The docstring says so outright — key derivation "is not intended to be used as a security method to make a complex key out of a short password. Instead you should use large random secret keys" ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L183-L187)).

> **For the owner:** The strength of every token this library issues is the entropy of `secret_key`, full stop. `derive_key` does one SHA-1 pass; it does not stretch, iterate, or slow anything down. A short or guessable secret is brute-forceable offline by anyone holding one token, because they can check a guess by recomputing the signature themselves. The scenario's literal `"secret key"` is README material, not deployment material. What to check before signing off: where the real secret comes from (environment, secret manager), how long it is, and that it is not in version control.

Also worth noting: the branch taken is chosen by an `if/elif` chain on a plain string, and `"none"` is one of the accepted values ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L210-L211)), which returns the secret key as the HMAC key with no derivation at all. Legal, occasionally wanted for compatibility, and it discards the salt's separating effect.

## The HMAC itself

With the derived key in hand, `get_signature` hands both it and the payload to the algorithm object built in chapter 3 ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L219)). `HMACAlgorithm.get_signature` is two lines ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L62-L64)):

```python
mac = hmac.new(key, msg=value, digestmod=self.digest_method)
return mac.digest()
```

The two `_lazy_sha1(string=b'')` calls the trace records inside this frame are `hmac.new` constructing its inner and outer hash objects — standard HMAC machinery. The message being authenticated is the *base64 payload bytes*, not the original dict and not the raw JSON: `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`. That matters for chapter 6, because it means the verifier can check the signature without decoding anything first.

Out comes a raw twenty-byte digest: `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`.

Raw bytes cannot go in a URL, so `get_signature` runs it through `base64_encode` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L220)) — the same URL-safe encoder, padding stripped, that shaped the payload in chapter 2 ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25)). Twenty bytes become twenty-seven characters: `b'6YP6T0BaO67XP--9UzTrmurXSmg'`. Notice those two hyphens — that is `urlsafe_b64encode`'s alphabet at work, and it is exactly why chapter 3's separator check refuses `-` as a `sep`.

## Joining up

Back in `sign`, the concatenation happens and the trace returns:

```
b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'
```

Payload, dot, signature. One `.` in the whole string, because base64 cannot produce one.

> **For the owner:** State the guarantee precisely, because it is narrower than people assume. This is **integrity and authenticity, not confidentiality**. The payload is base64, which is an encoding, not encryption — anyone holding the token can decode it and read `{"id":5,"name":"itsdangerous"}`. What they cannot do is change it, because any edit invalidates the HMAC. Never put anything in a token that the token's holder should not see. Also absent by construction: any notion of time. Nothing here expires, and nothing prevents the same token from being presented forever, or replayed after a user's session should have ended. If you need age limits, that is `URLSafeTimedSerializer`, a different class ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L79-L83)).

## One last decode

`dumps` receives the signed bytes and reaches its final branch ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L317-L320)):

```python
if self.is_text_serializer:
    return rv.decode("utf-8")
return rv
```

This is the boolean from chapter 1 finally being spent. `is_text_serializer` was set to `True` at construction, because a throwaway `_CompactJSON.dumps({})` returned the `str` `'{}'` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L33-L37), [serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L220)). So the bytes are decoded and the token leaves as a `str`. Had the caller supplied a binary serializer — `pickle`, say — the same code would have returned `bytes` instead, which is why the scenario's `assert isinstance(token, str)` is checking something real rather than a formality.

The decode is safe without a try/except because both halves are base64 from a URL-safe alphabet: pure ASCII, and ASCII is always valid UTF-8.

The trace prints it, and the dict's outbound journey is over:

```
token: eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg
```

Sixty-nine characters that can sit in a query string, a cookie, or an email link, carrying a user id and a name out into a place nobody controls — and carrying, stuck to the end, twenty-seven characters that only someone holding `b'secret key'` could have produced.

> **Leaves as:** `'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'` (a `str`)
