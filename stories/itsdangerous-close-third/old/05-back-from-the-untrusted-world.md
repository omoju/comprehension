# Chapter 5 · Back From the Untrusted World

> **Enters as:** `s='eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`, `salt=None`, arriving at `Serializer.loads`

In the scenario the token's trip through the untrusted world is a single line of Python — it goes into `token` and comes straight back out. In production it would be a URL a user clicked, a cookie a browser returned, a query string a proxy logged. From here on, the code treats it as if it had made that trip: nothing about it is believed until a signature says so.

`URLSafeSerializer` does not override `loads`, so the string lands in `Serializer.loads` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L328-L343)). Four lines of setup, then a loop.

## Normalising, again

```python
s = want_bytes(s)
last_exception = None
```

The trace shows `want_bytes(s='eyJpZCI6...Smg', encoding='utf-8', errors='strict')` returning the same sixty-eight characters as bytes ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)). This is the same normalisation the payload got on the way out, for the same reason: `loads` accepts `str` or `bytes` — callers pull tokens out of `request.args` (text) or a cookie jar (bytes) and either should work — and everything downstream compares bytes.

Note the `errors='strict'`. If a caller handed in a `str` containing characters that cannot be UTF-8 encoded, this raises `UnicodeEncodeError` rather than a `BadSignature`. For a token built out of URL-safe base64 that cannot happen from the code's own output, but it is a shape of failure worth knowing: garbage that isn't even encodable escapes the loop below entirely, as a `UnicodeError`, not a `BadData`.

The token is now `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`, and `last_exception` is `None`, waiting.

## Assembling the jury

```python
for signer in self.iter_unsigners(salt):
```

`iter_unsigners` is a generator ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L287-L307)). It is the list of candidate verifiers the token will be offered to, in order, and its order is the interesting part.

First, the salt default — the same substitution `make_signer` does, repeated here so the fallbacks get it too ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L292-L293)):

```python
if salt is None:
    salt = self.salt
```

The scenario passed no salt, so `salt` becomes `b'auth'` — the bytes stored at construction. This is what makes `dumps`-then-`loads` symmetric by default: both ends reach for the same attribute. The trace shows the consequence one line later, `make_signer(self=<URLSafeSerializer>, salt=b'auth')` — note that on the way out, in chapter 3, `make_signer` was called with `salt=None` and did the substitution itself. Same destination, different road.

Then:

```python
yield self.make_signer(salt)
```

The primary signer comes first, always ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L295)). The trace shows it being built exactly as in chapter 3 — `_make_keys_list([b'secret key'])`, `want_bytes(b'.')`, `want_bytes(b'auth')`, a fresh `HMACAlgorithm(_lazy_sha1)` — a brand-new `Signer` object at a different address than the one that signed. Signers hold no per-message state, so this costs one object and buys thread-safety by construction.

And then the loop that, here, does nothing:

```python
for fallback in self.fallback_signers:
```

`self.fallback_signers` is `[]` — the empty `default_fallback_signers` from chapter 1 — so the generator is exhausted after one yield. The trace confirms it: `iter_unsigners` returns after producing a single `Signer`.

**Reader, this empty list is a deliberate default and worth a moment.** Fallbacks exist so you can change signing parameters without invalidating every token already in the wild: you move the new parameters into `signer_kwargs` and list the old ones in `fallback_signers`, and tokens signed last week still verify while new ones use the new scheme ([serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L77-L104)). Each entry can be a dict of kwargs, a `Signer` subclass, or a `(class, kwargs)` tuple, and the code normalises the three shapes ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L297-L304)). Note also that fallbacks are constructed *one secret key at a time* — `for secret_key in self.secret_keys: yield fallback(secret_key, ...)` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L306-L307)) — whereas the primary signer receives the whole list and does its own key loop internally. Same coverage, different plumbing.

The security point: every fallback you add is another way a token can be accepted. The list was emptied in 2.0 precisely because the previous default silently accepted SHA-512 signatures that nobody had asked for ([CHANGES.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L95-L96)). Defaulting to "try exactly what I configured, and nothing else" is the right default; anything more permissive should be something you wrote down on purpose.

## The loop's shape, and what it swallows

The body is three lines ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L343)):

```python
for signer in self.iter_unsigners(salt):
    try:
        return self.load_payload(signer.unsign(s))
    except BadSignature as err:
        last_exception = err

raise t.cast(BadSignature, last_exception)
```

Two things a reviewer should notice before we follow the bytes into `unsign`.

**The catch is narrow.** Only `BadSignature` moves to the next candidate. `BadPayload` — which is a `BadData` but *not* a `BadSignature` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L92-L99)) — propagates immediately. So a token whose signature verifies but whose body is unloadable fails loudly rather than being quietly retried against every other key you have configured. That is the behaviour you want: a valid signature over junk is a bug or an attack, not a reason to keep guessing.

**Only the last exception survives.** Each rejection overwrites `last_exception`, and if every candidate fails, that final one is raised. With N fallbacks configured, the error your logs show comes from the *last* signer tried — quite possibly a legacy one — not the primary. It is not wrong, but it is a diagnostic sharp edge when you are debugging why a token stopped working.

(And if `iter_unsigners` ever yielded nothing at all, `last_exception` would still be `None`, and `raise None` surfaces as `TypeError`. `t.cast` is a type-checker annotation, not a runtime check. Reaching that requires deliberately overriding the generator to be empty; it is not a path this configuration can take.)

For now, the jury has one member. The token bytes go to it.

> **Leaves as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`, handed to the single candidate `Signer` (`secret_keys=[b'secret key']`, `salt=b'auth'`, `sep=b'.'`) yielded by `iter_unsigners`
