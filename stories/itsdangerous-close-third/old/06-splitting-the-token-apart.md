# Chapter 6 · Splitting the Token Apart

> **Enters as:** `signed_value=b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'`, handed to `Signer.unsign`

The sixty-eight bytes arrive at [`Signer.unsign`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L244-L256) as one undifferentiated string. Nothing here knows yet which part of it is the user's data and which part is the claim about that data. The first job is to cut it in two, and the second is to decide whether the two halves agree.

## Normalise once more

```python
signed_value = want_bytes(signed_value)
```

The trace shows it: `want_bytes(s=b'eyJpZCI6...Smg', ...)` returning the same bytes unchanged ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17)). `loads` already did this a moment ago, so it is a no-op here — but `Signer` is a public class in its own right ([signer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/signer.rst#L20-L22)), and a caller who reaches for `Signer.unsign` directly with a `str` gets the same treatment. The redundancy is the price of each layer defending its own entry point.

## The road not taken: no separator at all

```python
if self.sep not in signed_value:
    raise BadSignature(f"No {self.sep!r} found in value")
```

Before any hashing happens, `unsign` checks that the value even has the shape of a token ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L248-L249)). Our token contains `b'.'`, so we walk past this. If it hadn't — an empty string, a truncated cookie, a stray URL fragment — it would raise `BadSignature("No b'.' found in value")` immediately.

Two details for the reader. First, this happens *before* any key derivation or HMAC, so obviously-malformed input costs nothing. Second, and more interesting: this `BadSignature` is constructed with no `payload` argument, so `err.payload` is `None` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L25-L33)). That matters downstream — `loads_unsafe` inspects exactly that attribute and returns `(False, None)` when it is missing rather than trying to decode anything ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L382-L384)). Shapeless garbage is never offered back to the caller as a payload, even by the unsafe door.

## The cut

```python
value, sig = signed_value.rsplit(self.sep, 1)
```

`rsplit` with a count of 1: the **last** dot wins ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L251)). Our token has exactly one, so the split is unambiguous:

- `value = b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — the base64 payload built in chapter 2
- `sig = b'6YP6T0BaO67XP--9UzTrmurXSmg'` — the encoded HMAC from chapter 4

Splitting from the right is what makes the format robust. Recall from chapter 2 that a *compressed* URL-safe payload carries a leading `b"."` marker ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L66-L67)) — such a token has two dots, and `rsplit` still peels off the signature correctly, leaving the marker attached to the payload where `load_payload` expects it. What would *not* be recoverable is a dot inside the signature itself, which is why `Signer.__init__` rejects any separator drawn from the base64 alphabet back at construction time ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L146-L151)). The guarantee that this one line is unambiguous was bought three chapters ago.

## Decoding the claim

```python
if self.verify_signature(value, sig):
    return value
```

The two halves go to [`verify_signature`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L227-L242), which starts by turning the presented signature text back into raw bytes:

```python
try:
    sig = base64_decode(sig)
except Exception:
    return False
```

The trace records `base64_decode(string=b'6YP6T0BaO67XP--9UzTrmurXSmg')`, which internally calls `want_bytes(..., encoding='ascii', errors='ignore')` and returns the twenty raw digest bytes `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'` — byte for byte what `HMACAlgorithm.get_signature` produced on the way out in chapter 4.

Three choices in [`base64_decode`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L28-L38) deserve the reader's attention, because they decide how hostile input behaves:

- `errors="ignore"` on the ascii step: non-ASCII characters an attacker splices into the signature are silently dropped rather than raising. The result is simply a different byte string, which will fail to match.
- `string += b"=" * (-len(string) % 4)`: the padding stripped during encoding is put back, so the 27-character signature is re-padded to 28 before decoding.
- Genuinely undecodable input raises `BadData("Invalid base64-encoded data")` — but `verify_signature` wraps the call in a bare `except Exception: return False` ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L229-L232)). A malformed signature therefore becomes an ordinary verification failure, not a distinct exception type leaking out through `loads`. An attacker probing with broken base64 learns nothing that an attacker probing with well-formed wrong base64 wouldn't.

Then the value side is normalised one last time — the trace's `want_bytes(s=b'eyJpZCI6...cyJ9')`, unchanged ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L234)) — and the two are ready to be judged.

## If they disagree

We are on the happy path, but the failure line is the one an owner should read most carefully ([signer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L256)):

```python
raise BadSignature(f"Signature {sig!r} does not match", payload=value)
```

The unverified payload is deliberately attached to the exception. That is a design decision, not an oversight: the library refuses to decode tampered data for you, but it does hand you the bytes so *you* can decide ([serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L36-L64)). Calling `load_payload` on `e.payload` is an explicit, separately-named step precisely because it means running your deserializer over data you know someone modified. With the default JSON serializer the blast radius is small; with `pickle` it would be remote code execution. The separation is the safety rail.

Here, no exception. `verify_signature` returns `True` — chapter 7 is how — and `unsign` returns the payload half alone.

> **Leaves as:** `value = b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'`, with `sig` decoded to `b'\xe9\x83\xfaO@Z;\xae\xd7?\xef\xbdS4\xeb\x9a\xea\xd7Jh'` and awaiting comparison inside `verify_signature`
