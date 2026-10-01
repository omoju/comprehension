# Chapter 7 · The Verdict

> **Enters as:** `value = b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` and `sig = b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`, inside `Signer.verify_signature`, nothing decided yet

Everything so far has been preparation: encoding, splitting, re-padding. Now the library has to answer one question — *did someone holding a secret key produce this signature over these bytes?* — and it answers it in five lines.

## Every key, newest first

```python
for secret_key in reversed(self.secret_keys):
    key = self.derive_key(secret_key)

    if self.algorithm.verify_signature(key, value, sig):
        return True

return False
```

That is the whole verification policy ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L236-L242)). `self.secret_keys` is the list built in chapter 1 — here the single-element `[b'secret key']` that `_make_keys_list` produced from the string the caller passed ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L67-L73)) — so the loop runs exactly once, and the trace shows exactly one `derive_key` call.

The `reversed` is the interesting part. Signing used `secret_keys[-1]`, the newest key, and nothing else (chapter 4). Verification tries *all* of them, newest first, and accepts on the first match. That asymmetry is the entire key-rotation feature: append a new key and every token you mint from then on uses it, while tokens signed under the older keys keep validating until those keys are dropped from the list ([docs/concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L116-L134)).

> **For the owner:** There is no per-key expiry here and no revocation list. A key is valid for exactly as long as it appears in `secret_keys`; removing it is the *only* way to invalidate the tokens it signed, and doing so invalidates all of them at once. If you adopt rotation, the schedule that adds and removes entries lives in your code, not this library's — the docs are explicit that the rotation system is out of scope ([docs/concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L112-L114)). Worth asking: who owns that list, and what happens to a user whose token was signed with a key that aged out?

## The same key, derived the same way

```
Signer.derive_key(self=<Signer>, secret_key=b'secret key')
  want_bytes(s=b'secret key', ...) → b'secret key'
  _lazy_sha1(string=b'authsignersecret key') → <sha1 ...>
  → b'\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8'
```

This is the same twenty bytes that came out of `derive_key` during signing in chapter 4 — but it arrived by a slightly different route. Signing called `derive_key()` with no argument and took the default branch, `secret_key = self.secret_keys[-1]`. Verification passes a key explicitly, so the `else` branch runs and coerces it through `want_bytes` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L195-L198)). It is already bytes; nothing changes.

Then the `django-concat` branch, still the default nobody overrode ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L202-L205)):

```python
return self.digest_method(self.salt + b"signer" + secret_key).digest()
```

`b'auth'` + `b'signer'` + `b'secret key'` = `b'authsignersecret key'`, hashed. This is where the salt earns its keep. Two serializers sharing `"secret key"` but salted `"activate"` and `"upgrade"` derive different keys and cannot read each other's tokens ([docs/concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L56-L69)). It is also where the library is careful *not* to oversell: the docstring says plainly that key derivation "is not intended to be used as a security method to make a complex key out of a short password" ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L183-L187)). One SHA-1 over a concatenation is not a KDF. A guessable secret key stays guessable after derivation.

Had `key_derivation` been set to some string the code doesn't recognise, this is where it would have blown up — `raise TypeError("Unknown key derivation method")`, at first use rather than at construction ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L212-L213)).

## Recompute, then compare in constant time

The derived key, the payload and the presented signature go to [`SigningAlgorithm.verify_signature`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L24-L28) — the base-class method, inherited by `HMACAlgorithm`, which is why the trace names it `SigningAlgorithm.verify_signature(self=<HMACAlgorithm>, ...)`:

```python
return hmac.compare_digest(sig, self.get_signature(key, value))
```

Note what it does *not* do: there is no stored expected signature anywhere, and no attempt to reverse anything. It simply re-signs the payload from scratch. The trace shows `HMACAlgorithm.get_signature` running again ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L62-L64)) — `hmac.new` constructing its two internal SHA-1 states, which is the pair of `_lazy_sha1(string=b'')` calls — and producing `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`, identical to what came out of chapter 4 and identical to what chapter 6 decoded from the token's tail.

The comparison is `hmac.compare_digest`, not `==`. Constant-time: it does not return early at the first differing byte, so an attacker who can measure how long verification takes learns nothing about how many leading bytes of their forgery were correct. Without it, an adversary could in principle build a valid signature one byte at a time. With it, the only route to a matching HMAC is possession of a key.

`True` comes back, `verify_signature` returns `True`, and [`unsign`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L253-L254) hands the payload back:

```python
if self.verify_signature(value, sig):
    return value
```

`b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — the same bytes that went in, now vouched for. Had the loop fallen through to `return False`, the `BadSignature` from the end of chapter 6 would have been raised instead, carrying the payload as unverified bytes. Callers who want a plain boolean rather than an exception have [`Signer.validate`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L258-L266), which catches `BadSignature` and only that.

## What was just guaranteed, and by whom

This is the moment the library's promise is either kept or broken, so it is worth being precise about it. What has been established is that these payload bytes were signed by someone in possession of `b'secret key'` under the salt `b'auth'`. Nothing about *when*, nothing about *how many times*, nothing about secrecy — the payload has been readable base64 the whole trip.

And the guarantee rests on a default that is swappable. `self.algorithm` is whatever was configured; the base class is generic enough that a custom `SigningAlgorithm` could verify an asymmetric signature ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L15-L22)). It could also be `NoneAlgorithm`, which signs `b""` and would therefore accept an empty signature from anybody ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L31-L37)). The default — HMAC, constant-time — is the safe one, and no code in this run departed from it.

> **For the owner:** Two defaults reviewers reliably flag here. The first is SHA-1, and the answer is that its collision weaknesses do not apply to its use as the inner hash of an HMAC; the maintainers say so directly and offer a fallback-signer path for projects with a policy against it anyway ([docs/concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L137-L154)). The second is real: the security of this whole chapter reduces to `secret_keys` and to `algorithm` staying at its default. Grep for `algorithm=` and `key_derivation=` in your configuration, and confirm the secret key comes from the environment and is long and random rather than a memorable string ([docs/concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L20-L29)) — derivation will not rescue a weak one.

The bytes are trusted now. They are also still base64, and still not a dict.

> **Leaves as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, returned from `Signer.unsign` to `Serializer.loads`
