# Chapter 3 · The Failure Vocabulary

> **Inputs:** `BadData` as the base error raised by decoding (ch. 2), and the two gaps where a non-library exception escapes.
> **Code:** `src/itsdangerous/exc.py` — 106 lines, six classes, no logic.

Chapter 2 ended on a promise the encoder kept imperfectly: *malformed input becomes a library error*. To judge that promise you need to know what a library error **is** here — what it's called, what it carries, and what a handler written by a busy developer will and won't catch.

That is this whole file. It defines no behaviour. It defines a vocabulary, and the shape of that vocabulary determines what your application's `except` clauses actually mean.

## The root

[`BadData`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L7-L19) is the ancestor of every exception the library defines, and its docstring says so outright: *"This is the base for all exceptions that ItsDangerous defines."*

It is almost nothing. It takes a message, [stores it on `.message` and returns it from `__str__`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L14-L19). There is no error code, no category field, no machine-readable discriminator. If your handler needs to distinguish one failure from another, **it must do so by exception type**, because the only other thing in the box is English prose.

For an owner, the practical reading is: `except BadData` is the one clause that catches everything the library means to raise. Everything narrower catches a branch. And from chapter 2 you already know two things `except BadData` does *not* catch — `UnicodeEncodeError` and `struct.error`.

The root is raised directly in exactly one place, [when base64 decoding genuinely fails](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L35-L38). Everywhere else, a subclass is used.

## The one that matters: `BadSignature`

[`BadSignature`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L22-L33) is the failure your system exists to produce. Its docstring is a single line — *"Raised if a signature does not match"* — and it is what [`Signer.unsign` raises when verification fails](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L253-L256) and [when the token has no separator at all](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L248-L249).

But it is not empty. It carries [`.payload`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L28-L33), and the comment above it is the most security-relevant sentence in the file:

> *The payload that failed the signature test. In some situations you might still want to inspect this, even if you know it was tampered with.*

Read that as an owner. **When verification fails, the library hands the attacker's bytes back to your code, attached to the exception.** That is deliberate, documented, and useful — but it means the object your handler receives contains untrusted data in a normal-looking attribute. Anything that logs `repr(e.__dict__)`, ships the exception to an error tracker, or — worse — feeds `.payload` onward, is handling hostile input.

It is typed [`t.Any | None`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L25-L33), not `bytes`. At the signer level it is the value half of the split token; nothing in the class constrains it further.

Two smaller notes on the same theme. The message itself embeds attacker-controlled bytes: [`f"Signature {sig!r} does not match"`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L253-L256) interpolates the presented signature. `!r` escapes it, so this is a log-volume and log-noise concern rather than an injection one, but the size of that string is chosen by whoever sent the token. And `.payload` is not only for applications — [the library reads it itself](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/timed.py#L91-L93), using a failed signature's payload to keep working. We'll come back to why in chapter 6; for now just note that the attribute is load-bearing internally, not a debugging courtesy.

## The time branch, and a collapse worth knowing about

Three classes hang off `BadSignature` in a straight line.

[`BadTimeSignature`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L36-L57) adds [`.date_signed`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L49-L57): when the signature was made, so you can tell a user how stale their link is. Since 2.0 it is a timezone-aware `datetime` or `None` — never a naive datetime, never an `int`, a change [called out as breaking in the changelog](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L84-L91).

[`SignatureExpired`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L60-L63) subclasses it and adds nothing at all. Its entire content is its identity: *this is the too-old case, not the forged case.*

So the chain is `SignatureExpired` → `BadTimeSignature` → `BadSignature` → `BadData` → `Exception`. And here is the thing to check in your own codebase:

```python
except BadSignature:
    abort(401)
```

That clause catches a forged token, a truncated token, a token from a rotated-out key, **and** a perfectly authentic token that is forty seconds past its expiry — with no way to tell them apart unless the handler checks the type. These are different events. One is an attack; one is a user who left a tab open. They usually deserve different log levels, different metrics, and different messages to the user. The hierarchy makes conflating them the path of least resistance.

The inverse is also true and more interesting: because `SignatureExpired` *is* a `BadSignature`, a handler that only knows about forgery will treat expiry as forgery — and any code that reacts to `BadSignature` by retrying with different parameters will retry expired tokens too. Whether that actually happens is [a question about the retry loop](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L343), which is chapter 7's and chapter 8's business. Hold it.

## The one that is deliberately *off* the branch

[`BadPayload`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L92-L106) descends from `BadData` — and **not** from `BadSignature`. That is not an oversight; it is the file's one real design statement.

Its docstring explains the split: it means the payload *"is loaded despite an invalid signature, or … there is a mismatch between the serializer and deserializer."* In other words: the cryptography is finished and had nothing to say. What failed was turning bytes into an object. It carries [`.original_error`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L101-L106), the underlying JSON or zlib exception, so you can diagnose without losing the cause.

This is what makes chapter 2's promise hold at the outer layer too: the serializer [catches every exception the data serializer can throw and re-raises it as `BadPayload`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L264-L269), so a `json.JSONDecodeError` never reaches your handler wearing its own name.

But the placement has teeth. An application whose token handling is wrapped in `except BadSignature` will **not** catch `BadPayload` — it will get an uncaught exception and, most likely, a 500 instead of a 401. And the library's own code has the same shape: [the retry loop in `Serializer.loads` catches only `BadSignature`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L343). What that does to fallback signers and key rotation is **q3.1**, answered in chapter 7.

## The ghost

[`BadHeader`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L66-L89) is a `BadSignature` subclass with `.header` and `.original_error`, for *"serializers that have a header that goes with the signature."*

No such serializer exists in this package any more. `BadHeader` [arrived in 0.24](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L153-L160) for the JSON Web Signature serializers, and [JWS was removed in 2.1.0](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L51-L57) with a pointer to a dedicated library. The class stayed: it is [still exported at the top level](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/__init__.py#L4-L9) and [still documented](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/exceptions.rst#L6-L22), but nothing in the source raises it.

It is harmless. It is worth naming anyway, because "the docs list six exceptions" and "the code can produce five of them" are different facts, and only one of them belongs in your threat model. If a third-party subclass raises it, it will be caught by `except BadSignature` — which, given its parentage, is probably right.

## So what does a caller actually get?

This answers the question chapter 1 left open (**q1.2**). The API divides cleanly in two:

**Anything that returns data signals failure by raising.** `unsign` returns the verified bytes or raises; `loads` returns the object or raises. There is no sentinel, no `None`-on-failure, no partially-trusted return value. If you got a value back, the signature matched under some configured key.

**Anything that returns a bool returns only a bool.** [`Signer.validate`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L258-L266) is `unsign` wrapped in `except BadSignature: return False`, and [`verify_signature` returns `False` rather than propagating when the presented signature won't even decode](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L229-L232). These are predicates. They hand back no data and so can't hand back untrusted data. Note the narrowness of `validate`'s `except`: it swallows signature failures only, so a configuration error inside the signer still escapes as itself rather than being flattened into `False`.

There is exactly one exception-free path that returns *data*, and it is the one flagged as dangerous: `loads_unsafe`, which returns a `(signature_valid, payload)` tuple and [is documented as such](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L66-L74). Which raises the obvious follow-on, given that `BadSignature` is already carrying the tampered bytes around: **does anything deserialize that payload without the application asking?** That is **q3.2**, and chapter 7 settles it.

---

### What this chapter hands to the next

| | |
|---|---|
| **Characters** | `BadData` · `BadSignature` + `.payload` · `BadTimeSignature` + `.date_signed` · `SignatureExpired` · `BadHeader` · `BadPayload` + `.original_error` |
| **Facts** | `BadData` is the root of every intentional failure; the only discriminator is the exception *type* · `BadSignature.payload` hands attacker-controlled bytes back to the caller by design, and the library reads it internally too · `SignatureExpired` ⊂ `BadTimeSignature` ⊂ `BadSignature`, so `except BadSignature` conflates "forged" with "expired" · `date_signed` is tz-aware `datetime` or `None`, never naive, never `int` · `BadPayload` is a `BadData` but **not** a `BadSignature`: it means signing is done and deserialization failed · `BadHeader` is exported and documented but has no producer in this package since JWS was removed in 2.1 · the failure message embeds the attacker's signature bytes (repr-escaped) |
| **Answered** | *q1.2* — every data-returning call raises on failure; there is no partially-trusted return. Boolean predicates (`validate`, `verify_signature`) return `False` and no data. The single exception-free data path is `loads_unsafe`, documented as dangerous. |
| **Open questions** | *q3.1* `BadPayload` sits outside the `BadSignature` branch — what does that do to a retry/fallback loop? *(ch. 7)* · *q3.2* Is the tampered payload ever deserialized without the application asking? *(ch. 7)* |

### Proof

Runs from the repository root with `PYTHONPATH=src`.

```python proof
import pathlib

import itsdangerous
from itsdangerous.exc import (
    BadData,
    BadHeader,
    BadPayload,
    BadSignature,
    BadTimeSignature,
    SignatureExpired,
)
from itsdangerous.signer import Signer

# --- BadData is the root of everything the library defines. ---
for exc in (BadSignature, BadTimeSignature, SignatureExpired, BadHeader, BadPayload):
    assert issubclass(exc, BadData), exc
assert BadData.__bases__ == (Exception,)

# It carries a message and nothing else machine-readable.
e = BadData("boom")
assert e.message == "boom" and str(e) == "boom"

# --- The exact inheritance chain on the signature branch. ---
assert BadSignature.__bases__ == (BadData,)
assert BadTimeSignature.__bases__ == (BadSignature,)
assert SignatureExpired.__bases__ == (BadTimeSignature,)
assert BadHeader.__bases__ == (BadSignature,)

# ...so `except BadSignature` cannot tell "forged" from "expired".
try:
    raise SignatureExpired("age 15 > 5 seconds")
except BadSignature as caught:
    assert type(caught) is SignatureExpired  # only the type distinguishes them
else:
    raise AssertionError("SignatureExpired must be caught by except BadSignature")

# --- BadPayload is deliberately OFF that branch. ---
assert BadPayload.__bases__ == (BadData,)
assert not issubclass(BadPayload, BadSignature)
try:
    try:
        raise BadPayload("could not deserialize", original_error=ValueError("x"))
    except BadSignature:
        raise AssertionError("BadPayload must NOT be caught by except BadSignature")
except BadData as caught:
    assert isinstance(caught.original_error, ValueError)

# --- Attribute defaults and payloads. ---
assert BadSignature("m").payload is None
assert BadTimeSignature("m").date_signed is None
assert BadTimeSignature("m").payload is None
assert BadHeader("m").header is None and BadHeader("m").original_error is None
assert BadPayload("m").original_error is None

# --- A real failure hands the attacker's bytes back on .payload. ---
s = Signer("secret-key")
token = s.sign(b"user=42")
forged = token.replace(b"user=42", b"user=1", 1)
presented_sig = forged.rsplit(b".", 1)[1]

try:
    s.unsign(forged)
except BadSignature as caught:
    assert type(caught) is BadSignature
    assert caught.payload == b"user=1"             # untrusted value, handed back
    assert "does not match" in str(caught)
    assert repr(presented_sig) in str(caught)      # message embeds presented bytes
else:
    raise AssertionError("a forged token must not unsign")

# Predicates return only a bool, never data.
assert s.validate(token) is True
assert s.validate(forged) is False
assert s.verify_signature(b"user=1", presented_sig) is False

# --- Who actually raises what, in the shipped source. ---
src = pathlib.Path("src/itsdangerous")
text = {p.name: p.read_text() for p in src.glob("*.py")}

assert "raise BadData(" in text["encoding.py"]
assert "raise BadSignature(" in text["signer.py"]
assert "raise BadTimeSignature(" in text["timed.py"]
assert "raise SignatureExpired(" in text["timed.py"]
assert "raise BadPayload(" in text["serializer.py"]
assert "raise BadPayload(" in text["url_safe.py"]

# BadHeader is exported and documented, but nothing in the package raises it.
assert not any("raise BadHeader" in body for body in text.values())
assert {name for name, body in text.items() if "BadHeader" in body} == {
    "exc.py",
    "__init__.py",
}
assert "BadHeader" in pathlib.Path("docs/exceptions.rst").read_text()

# All six are part of the public surface.
for name in (
    "BadData",
    "BadSignature",
    "BadTimeSignature",
    "SignatureExpired",
    "BadHeader",
    "BadPayload",
):
    assert hasattr(itsdangerous, name), name
```
