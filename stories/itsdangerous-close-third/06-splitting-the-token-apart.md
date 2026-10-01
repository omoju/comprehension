# Chapter 6 · Splitting the Token Apart

> **Enters as:** `b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`, arriving at `Signer.unsign` on the single candidate signer

The bytes arrive at [`Signer.unsign`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L244-L256), which is the first place in the whole return journey that looks at the *shape* of the token rather than passing it along. It is eight lines, and each one is a decision about an untrusted string.

## Bytes again, harmlessly

```python
signed_value = want_bytes(signed_value)
```

The trace shows `want_bytes` called with the bytes it was already given and returning them unchanged ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L246), [encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)). `loads` had already normalised them in chapter 5; this second call is not waste but independence — `Signer` is a public class in its own right ([docs/signer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/signer.rst#L20-L22)), and someone calling `signer.unsign("some string")` directly must get the same treatment as someone coming through a serializer. Every entry point normalises; no entry point assumes an earlier one did.

## Is there a dot at all?

```python
if self.sep not in signed_value:
    raise BadSignature(f"No {self.sep!r} found in value")
```

This is the cheapest possible rejection, and it happens before a single hash is computed ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L248-L249)). A caller who hands over a bare word, an empty string, or a truncated token that lost its tail gets `BadSignature("No b'.' found in value")` immediately.

Two things about that road not taken. First, no key derivation runs, so the cost of a flood of malformed tokens is a substring search, not a SHA-1 per key per fallback. Second — and this matters more — the exception is constructed *without* a `payload` argument, so `BadSignature.payload` is `None` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L25-L33)). There is nothing sensible to hand back, and the code does not invent something. A caller using `loads_unsafe` on such a token gets `(False, None)` rather than a guess ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L382-L384)).

Our token has a dot. On we go.

## The last dot wins

```python
value, sig = signed_value.rsplit(self.sep, 1)
```

`rsplit` with a maximum of one split, from the right ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L251)). The trace records the result implicitly in the next call's arguments: `verify_signature(value=b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9', sig=b'6YP6T0BaO67XP--9UzTrmurXSmg')`. The payload from chapter 2 and the signature from chapter 4, cleanly separated.

Splitting from the right, rather than the left, is what makes the format unambiguous — and it only works because of the guard back in chapter 3. `Signer.__init__` refuses any separator that appears in `_base64_alphabet`, the ASCII letters, digits, `-`, `_` and `=` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L146-L151), [encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L42)). Because `.` can never occur inside a base64 signature, the rightmost dot is *always* the boundary. Dots inside the payload are therefore free — which is exactly what the URL-safe mixin relies on when it prefixes a compressed payload with `b"."` ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L66-L68)). A compressed token looks like `.eJy....sig`, and `rsplit` still finds the right seam.

> **For the owner:** The separator rule is enforced at construction, not at use ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L146-L151)) — a bad `sep` is a `ValueError` at start-up, loudly, rather than a token-parsing ambiguity discovered in production. If your code passes a custom `sep` through `signer_kwargs`, that is the guarantee protecting you, and it is one of the few places in this library that refuses input outright instead of returning a failure value.

## Decoding a signature you do not trust yet

`unsign` now calls [`verify_signature(value, sig)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L227-L242), and its first act is to turn the presented signature text back into raw bytes:

```python
try:
    sig = base64_decode(sig)
except Exception:
    return False
```

The `try` is deliberately total ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L229-L232)). `base64_decode` raises `BadData` on input that base64 cannot parse ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L35-L38)), but a garbled signature is not a *different kind* of failure from a wrong one — both mean "this token is not ours". Swallowing it and returning `False` means a caller sees one consistent `BadSignature` for tampering of any flavour, instead of a `BadData` leaking out of the crypto path with a different message and a different stack.

Inside, [`base64_decode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L28-L38) does two small repairs before decoding:

```python
string = want_bytes(string, encoding="ascii", errors="ignore")
string += b"=" * (-len(string) % 4)
```

The trace shows that first call: `want_bytes(s=b'6YP6T0BaO67XP--9UzTrmurXSmg', encoding='ascii', errors='ignore')` returning the same bytes. The `errors="ignore"` only bites when the input is `str` — here it is already bytes, so `want_bytes` returns it untouched ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L14-L17)). Then the padding is restored: the signature is 27 characters, `-27 % 4` is `1`, so a single `=` is appended to make a legal base64 group. Chapter 4 stripped that `=` to shorten the token ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L25)); this line puts it back. The two are a matched pair.

Out comes `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'` — twenty bytes, the length of a SHA-1 digest, and byte-for-byte the digest that `HMACAlgorithm.get_signature` produced in chapter 4. The signature has made the round trip through text and back without losing a bit.

Then the value gets the same normalising treatment it has had at every boundary — `want_bytes(b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9')`, unchanged ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L234)) — and the two byte strings stand ready for judgement.

## What happens if they don't match

It is worth naming the other exit now, because it is the one an attacker will meet. If `verify_signature` comes back `False`, the last line runs ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L256)):

```python
raise BadSignature(f"Signature {sig!r} does not match", payload=value)
```

Note the `payload=value`. Unlike the missing-separator case, here the code *does* attach the unverified payload to the exception — on purpose. The docs explain the reasoning: sometimes you want to inspect what someone tried to send you, for debugging or for logging, even knowing it is tampered with ([docs/serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L36-L64)). But the payload is attached *raw*: still base64, still undeserialised. Turning it into an object requires a separate, explicit `load_payload` call, precisely so that nobody deserialises attacker-controlled bytes by accident.

> **For the owner:** This is the design's clearest trust boundary, and it is enforced by shape rather than by discipline: a failed `unsign` hands you bytes, never an object. The risk lives entirely on the other side — if application code catches `BadSignature` and calls `load_payload(e.payload)`, it is deserialising unauthenticated input, and with the default JSON serializer that is merely unwise, while with a `pickle` serializer it is remote code execution ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L358-L361)). Two things to check before signing off: that no production path calls `load_payload` on a rejected token, and that nobody has passed `serializer=pickle` to a serializer reading data from users.

The payload and the recomputed-signature-to-be are now side by side. Nothing has been decided.

> **Leaves as:** `value = b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` and the decoded signature `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'`, inside `verify_signature`, awaiting key derivation and comparison
