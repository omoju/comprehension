# Chapter 5 · Back From the Untrusted World

> **Enters as:** `'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'` (a `str`), handed to `auth_s.loads`

The token comes back. In the scenario it never really left — it is handed straight from a local variable to `auth_s.loads` — but the code cannot know that, and its whole design assumes the opposite: that between chapter 4 and this line the string passed through a browser, a mail client, a proxy, and possibly an attacker. Everything from here on treats the sixty-nine characters as a claim, not a fact.

`Serializer.loads` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L328-L343)) is short enough to read whole:

```python
s = want_bytes(s)
last_exception = None

for signer in self.iter_unsigners(salt):
    try:
        return self.load_payload(signer.unsign(s))
    except BadSignature as err:
        last_exception = err

raise t.cast(BadSignature, last_exception)
```

## Back to bytes

First, `want_bytes` ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)). The trace records it receiving the `str` and returning `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'` — this time an actual conversion, not the no-op it was on the way out, because chapter 4 ended by decoding the bytes to text.

The round trip through `str` and back is lossless here for a mundane reason: the alphabet is URL-safe base64 plus a dot, so every character is ASCII, and UTF-8 encoding of ASCII is the identity. The signature will be checked over exactly the bytes that were signed.

Note also that the parameter is typed `str | bytes` and `want_bytes` accepts both ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L328-L330)). A caller pulling a token out of a cookie jar as bytes, or out of a query string as text, does not have to think about it. Nothing is validated yet — the string could be empty, could be a novel, could contain no dot at all. It is just bytes now.

## Choosing who gets to judge it

`last_exception = None`, and then the loop asks `iter_unsigners(salt)` for candidates. `salt` is `None`, because the scenario called `auth_s.loads(token)` with no salt argument.

`iter_unsigners` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L287-L307)) opens with the same defaulting move that `make_signer` used on the way out:

```python
if salt is None:
    salt = self.salt

yield self.make_signer(salt)
```

This is the symmetry that makes the round trip work at all. `dumps` with no salt signed under `b'auth'`; `loads` with no salt verifies under `b'auth'`. The trace shows it concretely: `iter_unsigners(salt=None)` immediately calls `make_signer(salt=b'auth')` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L278-L285)), which builds a brand-new `Signer` with `secret_key=[b'secret key']`, `salt=b'auth'`, `sep=b'.'`, and a fresh `HMACAlgorithm(_lazy_sha1)` — the same construction sequence narrated in chapter 3, `_make_keys_list` and all ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L129-L173)).

It is a *different object* from the one that signed — `0x10ce94050` here against `0x10cd174d0` in chapter 4 — carrying identical parameters. Signers hold no per-message state, so this costs one SHA-1's worth of work later and buys the guarantee that a signer cannot accidentally remember something about a previous token.

Had the caller passed an explicit salt — `auth_s.loads(token, salt="other")` — this line would have built a signer whose derived key differed in its first four bytes of input, and the verification in chapter 7 would simply have failed. That is the intended mechanism, not a bug: it is how an activation token is stopped from working as an upgrade token.

## The generator that yields once

`iter_unsigners` is a generator. Having yielded the primary signer, it would continue into the fallback loop ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L297-L307)):

```python
for fallback in self.fallback_signers:
    if isinstance(fallback, dict):
        kwargs = fallback
        fallback = self.signer
    elif isinstance(fallback, tuple):
        fallback, kwargs = fallback
    else:
        kwargs = self.signer_kwargs

    for secret_key in self.secret_keys:
        yield fallback(secret_key, salt=salt, **kwargs)
```

Here `self.fallback_signers` is `[]` — the empty default from chapter 1 — so the loop body never runs and the generator is exhausted after one item. The trace bears this out: `iter_unsigners` produces exactly one `Signer` and `loads` never comes back for a second.

The road not taken is worth understanding anyway, because it is where a real deployment's upgrade path lives. Each fallback entry may be a dict of `signer_kwargs` (applied to the configured signer class), a `(class, kwargs)` tuple, or a bare `Signer` subclass. That is how a team switches from SHA-1 to SHA-256 without invalidating every token already in the wild: sign with the new parameters, list the old ones as a fallback, and let tokens expire naturally. Note the ordering — the *current* signer is always tried first, and fallbacks are constructed one key at a time across `secret_keys`, whereas the primary signer receives the whole key list at once and will iterate it internally.

> **For the owner:** Two defaults to be aware of. `default_fallback_signers` is `[]` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L101-L104)) — since 2.0 there is no legacy signer silently accepting old-format tokens, which is the safe choice, and it means changing `signer_kwargs` on a running system invalidates every outstanding token unless you add the old parameters as a fallback. Conversely, anything you *do* put in `fallback_signers` is a standing acceptance of that parameter set: a fallback with a weakened `digest_method` or a `"none"` key derivation is an open door that stays open until someone removes the entry. Ask what is in that list and when each entry is scheduled to come out.

## What the loop does with failure

The loop's error handling is the other thing to read carefully, because it shapes what a caller sees when a token is bad. Every `BadSignature` is caught, stashed in `last_exception`, and the loop moves on ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L343)). If all candidates reject the token, the *last* exception is re-raised — not the first, not an aggregate. With several fallbacks configured, the message a caller sees ("Signature ... does not match", or "No b'.' found in value") comes from whichever signer happened to be tried last, which is not necessarily the most informative one. It is a diagnostic wrinkle, not a security hole: rejection is rejection.

One genuinely odd corner: if `iter_unsigners` ever yielded nothing, `last_exception` would still be `None` and the final line would execute `raise None`, which Python reports as `TypeError: exceptions must derive from BaseException` rather than any `BadData` subclass. Reaching it requires overriding `iter_unsigners` to produce an empty iterator — the stock code always yields at least the primary signer. Worth knowing only if someone on your team subclasses this.

Note too what is *not* caught. The `except` clause names `BadSignature` specifically, and `BadPayload` is a sibling under `BadData`, not a subclass of `BadSignature` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L22-L23), [exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L92-L99)). So a token with a *valid* signature over an undecodable body will not cause a quiet retry against the next signer; it escapes the loop immediately. That distinction pays off in chapter 8.

> **For the owner:** `loads` gives you one of two outcomes and nothing in between: the deserialised object, or an exception deriving from `BadData`. It never returns a partially-trusted value, and it never hands back the payload of a token it rejected. Callers who want to look at rejected data have to ask for it explicitly — `BadSignature.payload` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L25-L33)), or the honestly-named `loads_unsafe` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L349-L365)). If you find either of those in application code outside a debugging path, that is the line to question in review.

The loop body now calls `signer.unsign(s)` with the bytes. The token is about to be taken apart.

> **Leaves as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`, entering `Signer.unsign` on the single candidate `Signer(secret_keys=[b'secret key'], salt=b'auth', sep=b'.')`
