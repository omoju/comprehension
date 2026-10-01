# Chapter 3 · A Signer Is Built for the Job

> **Enters as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, back in `Serializer.dumps`

The payload comes home to line 314 of `dumps`, where it meets a small redundancy: `want_bytes(self.dump_payload(obj))` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L314)). It is already bytes — `dump_payload` promised that — so `want_bytes` looks at it, finds it is not a `str`, and hands it straight back ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)). The trace records the call and the identical return. It is a belt-and-braces line: a subclass could override `dump_payload` and return text, and this keeps the next step honest either way.

Now the payload has to wait. Before anything can sign it, a signer has to exist, and one does not yet — `dumps` calls `self.make_signer(salt)` with `salt=None` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L315)).

## Whose salt, and whose keys

`make_signer` is four lines and both of them matter ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L278-L285)):

```python
if salt is None:
    salt = self.salt
return self.signer(self.secret_keys, salt=salt, **self.signer_kwargs)
```

The `None` the caller passed is not "no salt" — it is "use mine". So `salt` becomes `b'auth'`, the bytes stored at construction. This is the mechanism behind a guarantee worth stating plainly: because `dumps` and `loads` both funnel through `make_signer`, and both substitute the serializer's own salt when none is given, a token made by `auth_s.dumps(...)` is always readable by `auth_s.loads(...)`. The two ends cannot drift apart by accident. (If you *do* pass a salt to `dumps`, you must pass the same one to `loads` — that is the `test_alt_salt` case, and it fails with `BadSignature` if you forget.)

The second line hands over `self.secret_keys` — the whole list, `[b'secret key']`, not one key — plus `self.signer_kwargs`, which is `{}` here. The trace shows the constructor receiving exactly that: `secret_key=[b'secret key'], salt=b'auth', sep=b'.', key_derivation=None, digest_method=None, algorithm=None`.

> **For the owner:** This is where a caller's `signer_kwargs` reaches the cryptography — `digest_method`, `key_derivation`, `algorithm`, `sep` all arrive here unvalidated by the serializer. The serializer itself contributes no defaults for them; every default in the next section is the `Signer` class's own. If you want to know what algorithm a deployment is actually signing with, read `signer_kwargs` at the call site, not this file.

## The separator is checked before anything else

Inside `Signer.__init__` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L129-L173)) the list of keys goes through `_make_keys_list` a second time ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L67-L73)). It was already `[b'secret key']`, but the function does not know that; it sees an iterable that is neither `str` nor `bytes`, so it takes the comprehension branch and runs `want_bytes` over each element, producing a fresh `[b'secret key']`. Idempotent, cheap, and it means `Signer` is equally safe to construct directly with a raw string, as the docs show.

Then `sep`. `want_bytes(b'.')` gives `b'.'`, and immediately:

```python
if self.sep in _base64_alphabet:
    raise ValueError(...)
```

([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L146-L151)). `_base64_alphabet` is the bytes of `A-Za-z0-9-_=` ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L42)) — precisely the characters that can appear inside a base64-encoded signature. `b'.'` is not among them, so construction proceeds. Had someone passed `sep="-"`, this line would have raised `ValueError` here, at construction time, rather than producing tokens that split ambiguously when read back. It is a small guard in a constructor doing the work of a whole class of runtime bugs: the reader will use `rsplit(sep, 1)`, and that is only unambiguous if the signature cannot contain the separator.

> **For the owner:** This check is a genuine fail-fast: a bad separator is rejected the moment a `Signer` is built, not the moment a token fails to verify. Worth knowing it exists, because the equivalent mistake one line below is *not* caught — see the defaults.

## Defaults, and one that waits to complain

The remaining fields fill in from class attributes ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L153-L173)). `salt` is not `None`, so `want_bytes(b'auth')` returns `b'auth'` and it is stored. `key_derivation` is `None`, so it becomes `default_key_derivation`, the string `"django-concat"` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L127)). `digest_method` is `None`, so it becomes `default_digest_method`, the function `_lazy_sha1` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L120)).

That `_lazy_sha1` is not a mistake for `hashlib.sha1`. It is a one-line wrapper that defers the attribute access to call time ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L40-L45)) — the docstring says why: FIPS builds may not ship SHA-1, and touching `hashlib.sha1` at import time would blow up the whole library before a developer had any chance to configure a different digest. Nothing has been hashed yet at this point in the trace; the first `_lazy_sha1` call comes in the next chapter.

Note the asymmetry with the separator check. `key_derivation` is stored as whatever string arrived, with no validation. A typo — `"hmc"` instead of `"hmac"` — survives construction happily and raises `TypeError("Unknown key derivation method")` only later, from inside `derive_key` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L212-L213)), on the first attempt to sign or verify.

Finally, `algorithm` is `None`, so the constructor builds one: `HMACAlgorithm(self.digest_method)`, which simply stores the digest function ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L56-L60)). The trace shows it receiving `digest_method=<function _lazy_sha1>`.

> **For the owner:** The default is HMAC, and it is the safe one — but `algorithm` is an open extension point, and `NoneAlgorithm` lives one class away in the same file, returning `b""` for every signature ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L31-L37)). A serializer configured with `signer_kwargs={"algorithm": NoneAlgorithm()}` produces tokens that anyone can forge, and nothing in this constructor objects. On SHA-1 specifically: it is used here only as HMAC's inner hash, where collision resistance is not what the security rests on, and the project documents that reasoning. If policy forbids SHA-1 regardless, `signer_kwargs={"digest_method": hashlib.sha512}` is the knob, with a fallback signer for old tokens.

`__init__` returns `None`, `make_signer` returns the object, and the trace records `<itsdangerous.signer.Signer object at 0x10cd174d0>`. Worth noticing: this signer was built fresh for this one `dumps` call. `Serializer` keeps no signer around — it keeps the *ingredients* and assembles one on demand, and will assemble another in chapter 5 when the token comes back. Signers hold no per-message state, so nothing carries over between calls, and nothing is shared across threads by accident.

The payload has not moved. It is still forty bytes of base64 sitting in a local variable, waiting. What has changed is that there is now something in the room that knows the secret.

> **Leaves as:** the same `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, now paired with a fresh `Signer(secret_keys=[b'secret key'], salt=b'auth', sep=b'.', key_derivation='django-concat', digest_method=_lazy_sha1, algorithm=HMACAlgorithm(_lazy_sha1))`
