# Chapter 7 · The Verdict

> **Enters as:** inside `Signer.verify_signature`, holding `value = b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` and the decoded `sig = b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`

Two byte strings, and a question that has to be answered without the answer leaking. The payload claims to be `{"id":5,...}` signed under the `auth` context; the twenty bytes beside it claim to prove it. The only way to check is to compute what the signature *should* be and see whether it matches.

## Which key, in which order

```python
for secret_key in reversed(self.secret_keys):
    key = self.derive_key(secret_key)

    if self.algorithm.verify_signature(key, value, sig):
        return True

return False
```

That loop is the whole verification policy ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L236-L242)). It walks `secret_keys` **backwards** — newest first — and returns on the first key that validates. Our signer holds exactly one, `[b'secret key']`, so the trace shows a single pass: `Signer.derive_key(self=<Signer>, secret_key=b'secret key')`.

This asymmetry is worth naming for the reader, because it is where key rotation lives. Signing, back in chapter 4, used `self.secret_keys[-1]` and nothing else — one key writes ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L195-L196)). Verifying tries them all. So an operator can append a new key, keep serving old tokens, and later drop the oldest entry to invalidate everything signed with it ([concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L101-L134)). The flip side is the thing to put on a checklist: **a key stays valid for as long as it stays in the list.** There is no expiry here, no revocation list. Removing the key from the list *is* the revocation mechanism.

Note also that the loop derives the key fresh on every iteration — no caching. With a long key list, a forged token costs one hash per key before it is rejected.

## Deriving the key, again

`derive_key` is called this time *with* an argument, so it takes the branch the signing path skipped ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L195-L198)):

```python
if secret_key is None:
    secret_key = self.secret_keys[-1]
else:
    secret_key = want_bytes(secret_key)
```

The trace confirms it: `want_bytes(s=b'secret key', ...)` → `b'secret key'`, unchanged, since the key was already bytes from `_make_keys_list`. Then the same `django-concat` scheme as before ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L202-L205)):

```python
self.digest_method(self.salt + b"signer" + secret_key).digest()
```

`_lazy_sha1(string=b'authsignersecret key')` in the trace, returning `b'\xcea\x91\xbb\x97+C\x86\xdc\x0f\x82\xd1uM\xbf\x16\r\xa8\xff\xd8'` — bit for bit the key that signed the token. The salt `b'auth'` is baked in as a literal prefix, which is exactly why a serializer configured with a different salt derives a different key and rejects this token outright. The salt does not have to be secret to do that job.

(It is still not a KDF. The docstring says so plainly: derivation "is not intended to be used as a security method to make a complex key out of a short password" ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L183-L187)). A guessable secret key remains guessable after one round of SHA-1.)

## The comparison

The derived key, the payload, and the presented signature now go to the algorithm object — and here the trace reveals something the class names hide. It records `SigningAlgorithm.verify_signature(self=<HMACAlgorithm>, ...)`: `HMACAlgorithm` doesn't override this method, so the base class's implementation runs ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L24-L28)):

```python
return hmac.compare_digest(sig, self.get_signature(key, value))
```

One line, two guarantees.

`self.get_signature(key, value)` recomputes the HMAC from scratch ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L62-L64)) — the trace shows the two internal `_lazy_sha1(string=b'')` calls that `hmac.new` makes to set up its inner and outer digests, then the result `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`. Identical to the twenty bytes that arrived. Nothing about the incoming signature influenced that computation; it was derived only from the key and the payload.

And the equality test is `hmac.compare_digest`, not `==`. That is the security-relevant choice on this line: a naive byte comparison short-circuits on the first differing byte, and an attacker who can time thousands of requests can walk a forged signature into existence one byte at a time. `compare_digest` takes the same time regardless of where the strings diverge. It is the kind of detail nobody notices until it is missing.

`True` comes back, and `True` propagates out of `Signer.verify_signature`.

On the road not taken: had every key failed, `verify_signature` would return `False`, and `unsign` would raise `BadSignature("Signature b'...' does not match", payload=value)` — the failure line from the end of chapter 6. For callers who want a boolean instead of an exception there is [`Signer.validate`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L258-L266), which catches `BadSignature` and only `BadSignature` — a deliberately narrow net.

## What the `True` is worth

Two things about the shape of this check matter to whoever has to vouch for it.

First, the verification is generic by design. `algorithm` is an injection point ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L170-L173)), and `SigningAlgorithm.verify_signature` is overridable — the release notes call this out as support for asymmetric schemes ([CHANGES.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L172-L179)). That flexibility includes [`NoneAlgorithm`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L31-L37), which returns `b""` as the signature and would therefore accept an empty signature from anyone. It exists, it is documented, and the default is not it. If you are reviewing a codebase that passes `algorithm=`, that is the line to read.

Second, SHA-1. It will show up in any scanner's report. Used as the iterated hash inside HMAC, its collision weakness does not apply, and the project says so explicitly ([concepts.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L137-L154)). The pragmatic reason it is reached through `_lazy_sha1` rather than named at import time is FIPS builds, where `hashlib.sha1` may not exist — deferring the lookup gives the developer a chance to configure something else before it is ever touched ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L40-L45)).

So: the token was not modified, and whoever produced it held `b'secret key'` and used the salt `auth`. That is the entire guarantee — tamper-evidence and authenticity. Not confidentiality, not freshness. `unsign` returns the verified half ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L253-L254)), and the signature bytes, having done their work, are dropped.

What comes back is still base64. It still has to become a dict.

> **Leaves as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — verified bytes, returned from `Signer.unsign` to `Serializer.loads`
