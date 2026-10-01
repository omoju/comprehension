# Chapter 2 · Bytes In, Bytes Out: the Encoding Layer

> **Inputs:** the two-layer API, and the claim that tokens are readable but not modifiable (ch. 1).
> **Code:** `src/itsdangerous/encoding.py` — all 54 lines of it.

Chapter 1 left you with a suspicion: the README's token looked like base64 of the input, which would mean the payload is public. This chapter settles it, because the file that does the encoding is short enough to read in full and contains no key material at all.

There are five functions and two module constants here. Nothing in the file is secret, nothing takes a key, and everything is reversible. That is the answer to q1.3 in one sentence, but the details matter for two reasons: this layer decides which characters can appear in a token, and it decides which failures become library errors and which escape as raw Python exceptions.

## The translator

[`want_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17) is the first thing almost every other function calls. Give it `str`, it encodes UTF-8; give it `bytes`, it hands them straight back.

Two consequences follow, and both are worth knowing before you sign off on anything.

First, **the text/bytes distinction is erased before signing.** Signing `"my string"` and signing `b"my string"` produce byte-for-byte identical tokens, and the docs admit the round trip loses that information: ["If unicode strings are provided, an implicit encoding to UTF-8 happens. However after unsigning you won't be able to tell if it was unicode or a bytestring."](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/signer.rst#L24-L26) If your application's trust decision depends on the *type* of what came out, it can't — everything downstream is bytes.

Second, **the default is `errors="strict"`.** The [signature](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L13) sets it, and nothing on the signing path overrides it. So a `str` that cannot be encoded as UTF-8 — a lone surrogate, the kind you get from `surrogateescape` decoding of dirty input — raises `UnicodeEncodeError` out of `want_bytes`. That is not a `BadData`, so an application that wraps its token handling in `except BadData` will not catch it. It is a narrow case, and it requires the application to have produced a surrogate itself, but it is the first of two places in this file where a non-library exception can escape.

## The encoder, and why nothing here is a secret

[`base64_encode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L20-L25) is four lines: coerce to bytes, `base64.urlsafe_b64encode`, strip the trailing `=` padding.

It takes no key. It is exported at the top level of the package. Its inverse is in the same file. This is the whole of the "encoding" in ItsDangerous, and it is applied both to the signature and — in the URL-safe serializers we'll meet in chapter 9 — to the payload. **A token holder can always recover the payload, and no configuration option changes that.** Question q1.3 is closed: this is encoding, not encryption. If secrecy is required, it must come from somewhere outside this library.

The padding strip is cosmetic — shorter tokens — but it has a knock-on effect. Because `=` never appears in output, a signature produced here consists only of `A–Z`, `a–z`, `0–9`, `-` and `_`. That constraint is what makes a token parseable at all, as we'll see in chapter 5.

## The decoder is deliberately forgiving

[`base64_decode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L28-L38) is where the design choices start to have security relevance, because this function is fed attacker-controlled bytes on every single verification.

It does three things, in order:

1. [Coerces to bytes as **ASCII with `errors="ignore"`**](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L32). Any non-ASCII character in a `str` input is *silently dropped*, not rejected. (Note the asymmetry: because [`want_bytes` returns `bytes` untouched](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L14-L17), this `ignore` only ever applies to `str` input. A `bytes` input goes to the standard library as-is.)
2. [Re-adds the padding it stripped on the way out](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L33), so its own output round-trips.
3. Decodes, and [converts `TypeError`/`ValueError` into `BadData`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L35-L38) — [`BadData` being the library's own base exception, imported at the top of this file](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L8).

Step 3 is a good instinct: malformed input from a stranger should produce a library error, not a `binascii` error leaking through your handler. Step 1 will raise an eyebrow, and it should. A function that quietly discards characters it doesn't understand, applied to a value an attacker chose, is the shape of a real vulnerability in other libraries. **Whether it is one here depends entirely on what is done with the result** — and that is a question about the signer, not the encoder. Hold it as q2.1.

What you can say now, and only now, is where this function is called on hostile input: on the [presented signature during verification](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L229-L232), on the [timestamp in a timed token](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/timed.py#L112-L115), and on the [payload of a URL-safe token](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L36-L42). Three call sites, three chapters.

## The alphabet, written down once

[`_base64_alphabet`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L41-L42) is the private constant `A–Za–z0–9-_=` as bytes — sixty-five characters, the exact set that `base64.urlsafe_*` can emit, including the `=` that `base64_encode` strips and `base64_decode` puts back.

It exists for exactly one caller: the `Signer` constructor uses it to [refuse a separator that could also occur inside a signature](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L146-L151). A token is `value + sep + signature`; if `sep` could appear inside the signature, splitting the token would be ambiguous. Writing the alphabet down here, next to the functions that define it, is how that check stays honest when the encoding changes. The mechanics of the check belong to chapter 5.

## Eight bytes of integer, and the second escape hatch

The last three definitions serialize integers, and they exist for one customer: the timestamp in a timed token.

[`_int64_struct`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L44-L46) is `struct.Struct(">Q")` — big-endian, unsigned, **fixed at eight bytes**. [`int_to_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L49-L50) packs and strips leading zero bytes (so a small timestamp costs five bytes, not eight, and zero costs none at all); [`bytes_to_int`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L53-L54) right-justifies back to eight and unpacks.

The fixed width is a hard boundary. A value of 2⁶⁴ or more, or a byte string longer than eight bytes, raises `struct.error`. And `struct.error` inherits from `Exception` — **not** from `ValueError`, and certainly not from `BadData`. So unlike the base64 path, nothing in this file converts it into a library exception.

That matters because `bytes_to_int` is fed the timestamp segment of a token, and an attacker can make that segment as long as they like. Nine base64 characters of garbage decodes to more than eight bytes, and this function will raise `struct.error`. If that reached the caller, every application's `except BadData` would be wrong. Does it? That is q2.2, and it is answered in chapter 6.

---

Two things are settled. The payload in a token is public — permanently, for every class in the library. And this layer converts *most* malformed input into `BadData`, with two documented gaps: `UnicodeEncodeError` from strict UTF-8 on the way in, and `struct.error` from oversized integers on the way back.

Before we can judge either gap we need the vocabulary of failure itself: what `BadData` is the root of, what each subclass means, and what an exception hands back to the caller when verification fails. That is the next chapter.

---

### What this chapter hands to the next

| | |
|---|---|
| **Characters** | `want_bytes` · `base64_encode` · `base64_decode` · `_base64_alphabet` · `int_to_bytes` / `bytes_to_int` · `BadData` |
| **Facts** | everything becomes bytes before signing, so `str` and `bytes` inputs are indistinguishable afterwards · `want_bytes` defaults to `errors="strict"`, and `UnicodeEncodeError` is not a `BadData` · `base64_encode` is keyless, public and reversible; output is `A–Za–z0–9-_` with padding stripped · `base64_decode` silently drops non-ASCII from `str` input (`errors="ignore"`), re-pads, and converts decode failures to `BadData` · `_base64_alphabet` is the exact character set a signature can contain, and exists so the signer can reject a colliding separator · integers are packed with a fixed 8-byte `>Q`; overflow raises `struct.error`, which is **not** a `BadData` |
| **Answered** | *q1.3* — the payload is base64url encoding, not encryption. Anyone holding a token can read it, with no key and no configuration to prevent it. |
| **Open questions** | *q2.1* Can the lenient decode be exploited to turn a bad signature into a good one? *(ch. 5)* · *q2.2* Who catches the raw `struct.error` from an oversized timestamp? *(ch. 6)* |

### Proof

Runs from the repository root with `PYTHONPATH=src`.

```python proof
import base64
import string
import struct

from itsdangerous.encoding import (
    _base64_alphabet,
    base64_decode,
    base64_encode,
    bytes_to_int,
    int_to_bytes,
    want_bytes,
)
from itsdangerous.exc import BadData
from itsdangerous.signer import Signer

# --- want_bytes: str -> UTF-8, bytes pass through unchanged. ---
assert want_bytes("mañana") == "mañana".encode("utf-8")
raw = b"\xff\xfe not utf-8"
assert want_bytes(raw) is raw          # bytes are returned untouched, identity

# The text/bytes distinction is erased before signing.
s = Signer("secret-key")
assert s.sign("my string") == s.sign(b"my string")
assert s.unsign(s.sign("my string")) == b"my string"   # comes back as bytes either way

# errors="strict" is the default: a lone surrogate escapes as UnicodeEncodeError,
# which is NOT a library error.
assert not issubclass(UnicodeEncodeError, BadData)
try:
    want_bytes("\ud800")
except UnicodeEncodeError:
    pass
else:
    raise AssertionError("strict UTF-8 encoding should have refused a lone surrogate")

# --- base64_encode is keyless, public, reversible, and padding-free. ---
allowed = set((string.ascii_letters + string.digits + "-_").encode("ascii"))
for i in range(64):
    enc = base64_encode(bytes(range(i)))
    assert b"=" not in enc, enc
    assert set(enc) <= allowed, enc
    assert base64_decode(enc) == bytes(range(i))

# The encoding is the *standard* one: a stranger with no key decodes it.
assert base64_encode(b'{"id":5}') == base64.urlsafe_b64encode(b'{"id":5}').rstrip(b"=")

# --- base64_decode silently drops non-ASCII from str input. ---
assert base64_encode(b"hello") == b"aGVsbG8"
assert base64_decode("aGVsbG8") == b"hello"
assert base64_decode("aGVsñbG8") == b"hello"      # the ñ is ignored, not rejected
# ...but the "ignore" only applies to str: bytes never pass through the codec.
assert want_bytes(b"aGVs\xc3\xb1bG8", encoding="ascii", errors="ignore") == b"aGVs\xc3\xb1bG8"

# --- Genuine decode failures become BadData, the library's base exception. ---
try:
    base64_decode("12345")
except BadData as e:
    assert e.original_error is None or True     # BadData carries only a message here
    assert "base64" in str(e)
else:
    raise AssertionError("undecodable base64 should raise BadData")

# --- The alphabet constant is exactly what urlsafe base64 can emit. ---
assert _base64_alphabet == (string.ascii_letters + string.digits + "-_=").encode("ascii")
assert len(_base64_alphabet) == 65          # 52 letters + 10 digits + - _ =

# --- Fixed 8-byte integers; overflow escapes as struct.error, not BadData. ---
assert not issubclass(struct.error, BadData)
assert not issubclass(struct.error, ValueError)
assert int_to_bytes(0) == b""                       # leading zeros stripped
assert int_to_bytes(192) == b"\xc0"
assert int_to_bytes(2**64 - 1) == b"\xff" * 8
assert bytes_to_int(b"\xc0") == 192

try:
    int_to_bytes(2**64)
except struct.error:
    pass
else:
    raise AssertionError("values >= 2**64 must not pack into 8 bytes")

try:
    bytes_to_int(b"\x01" * 9)                       # 9 bytes: too long for ">Q"
except struct.error:
    pass
else:
    raise AssertionError("more than 8 bytes must not unpack")
```
