# Chapter 8 · Home Again, and What Was Promised

> **Enters as:** `payload = b'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9'` — forty bytes of verified base64, handed to `Serializer.loads`' next call

The signature has done its work and fallen away. What `loads` holds now is the same run of base64 the dict was folded into back in chapter 2, and the only thing left to do is unfold it. One line does it ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L339)):

```python
return self.load_payload(signer.unsign(s))
```

`self` is a `URLSafeSerializer`, so `self.load_payload` is the mixin's override, not the base class's. The trace names it exactly: `URLSafeSerializerMixin.load_payload(self=<URLSafeSerializer>, payload=b'eyJ...J9', serializer=None)`.

## Looking for the dot

The first thing that happens to the payload is a question about its very first byte ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L30-L34)):

```python
decompress = False

if payload.startswith(b"."):
    payload = payload[1:]
    decompress = True
```

This is the other half of a contract signed in chapter 2. There, `dump_payload` compressed the JSON with zlib, found the result no shorter than `len(json) - 1`, threw it away, and therefore did *not* prepend the marker byte ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L55-L69)). Our payload begins with `e`, not `.`, so `decompress` stays `False` and the bytes pass through untouched. The whole compression scheme is carried by that single leading byte — there is no length field, no version, no header. It works because the base64 alphabet cannot produce a `.` and the separator cannot be a base64 character; the dot is unambiguous wherever it appears.

## Base64, then JSON

`base64_decode` is called on the payload ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L36-L42)), and the trace shows it doing the reverse of chapter 2's encode: `want_bytes(s=b'eyJ...', encoding='ascii', errors='ignore')`, then re-padding and decoding ([encoding.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L28-L38)). Out comes `b'{"id":5,"name":"itsdangerous"}'` — the exact thirty bytes `_CompactJSON.dumps` produced on the way out.

Had the bytes been garbage, the `except Exception` around the call would have converted the failure into `BadPayload("Could not base64 decode the payload because of an exception", original_error=e)`. Had the marker byte been present over non-zlib data, the parallel guard a few lines down would have raised `BadPayload("Could not zlib decompress the payload before decoding the payload")` ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L44-L51)). In both cases the underlying exception is kept on `original_error`, so a log line can say *why* without the caller catching zlib errors.

Then the mixin hands the decoded JSON up to the base class ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L53)), and the trace records `Serializer.load_payload(self=<URLSafeSerializer>, payload=b'{"id":5,"name":"itsdangerous"}', serializer=None)`.

Here the boolean computed once at construction — the throwaway `dumps({})` probe from chapter 1 — is spent for the second and last time ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L252-L263)):

```python
if is_text:
    return use_serializer.loads(payload.decode("utf-8"))

return use_serializer.loads(payload)
```

`is_text_serializer` was `True`, so the bytes are decoded to `str` first, and the trace shows `_CompactJSON.loads(payload='{"id":5,"name":"itsdangerous"}')` receiving text ([_json.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/_json.py#L10-L12)). It returns `{'id': 5, 'name': 'itsdangerous'}`, which climbs back out through `Serializer.load_payload`, `URLSafeSerializerMixin.load_payload`, and finally `Serializer.loads`. The dict is home.

Note one thing on the way up. **The `serializer` keyword the mixin accepts is never forwarded.** It is declared keyword-only ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L23-L29)) and then left out of the `super()` call, which passes only `*args, **kwargs` ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L53)). So a caller who writes `url_safe_serializer.load_payload(p, serializer=pickle)` gets the configured serializer anyway, silently. It made no difference on our path — the trace's `serializer=None` was headed for the same branch — but it is the kind of quiet no-op a reviewer should know about before relying on it. (The proof below demonstrates it.)

## Where the errors go

Two failure modes are worth separating, because they are handled very differently.

A bad *signature* is a `BadSignature`, and `loads` catches it, remembers it, and tries the next signer ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L337-L343)). A bad *payload* is a `BadPayload`, which subclasses `BadData` and **not** `BadSignature` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L92-L106)). It therefore escapes the retry loop immediately. That is the right call: a payload that carried a valid signature but cannot be decoded means your serializer configuration changed, not that someone forged a token, and quietly trying the next key would hide it.

And notice what `Serializer.load_payload` wraps: *everything* the inner serializer throws ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L264-L269)). A caller who catches `BadData` around `loads` has caught the whole surface of this library's failures; no `json.JSONDecodeError` or `UnicodeDecodeError` leaks out.

## The one place unverified bytes get decoded

On the happy path, decompression and JSON parsing happen strictly *after* `unsign` returned successfully. Attacker-controlled zlib is never fed to `zlib.decompress` unauthenticated.

But `load_payload` is public, and the documentation actively recommends calling it on `BadSignature.payload` — the unverified bytes chapter 6 attached to the exception — for debugging, with an explicit warning that the decode step is separate precisely because it might be unsafe ([serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L44-L64)). `loads_unsafe` does the same thing behind a boolean ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L389-L395)). If you take that road with a URL-safe serializer, you are running `zlib.decompress` on bytes an attacker chose — a decompression bomb is the realistic worry — and then parsing them. The names say "unsafe"; they mean it.

Which brings up the single most consequential default in the whole library: the inner serializer is `json`, and for URL-safe serializers `_CompactJSON` ([serializer.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L92-L95), [url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L21)). Swapping in `pickle` is a supported constructor argument, and the docs tell you not to combine it with the unsafe loaders ([serializer.rst](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/serializer.rst#L58-L64)). With JSON, `load_payload` on hostile bytes is a parse error. With pickle, it is arbitrary code execution. That is the question to ask of any codebase using this library: *what did you pass as `serializer`?*

## What was promised

The dict went out as `'eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg'` and came back as `{'id': 5, 'name': 'itsdangerous'}`. The guarantee behind that round trip, stated plainly:

- **The returned object was produced by someone holding one of `secret_keys`, under salt `b'auth'`.** Nothing else about it is asserted.
- **Not confidential.** The payload is base64, not ciphertext; anyone can read `{"id":5,...}`. A user id in a token is a user id in public.
- **Not fresh.** There is no timestamp and no replay protection. A token is valid until the key that signed it leaves the list. If you need age limits, that is `URLSafeTimedSerializer` ([url_safe.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L79-L83)) and its `max_age` check ([timed.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/timed.py#L137-L153)) — a different class, chosen deliberately, not a flag you can forget to turn on.
- **Failures are typed.** Everything this library rejects raises a subclass of `BadData` ([exc.py](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/exc.py#L7-L19)); nothing returns a quietly wrong value.
- **The risky doors are labelled.** `loads_unsafe`, `load_payload` on `e.payload`, `NoneAlgorithm`, `serializer=pickle`. None is reachable by accident.

> **Leaves as:** `{'id': 5, 'name': 'itsdangerous'}` — the caller's dict, returned from `Serializer.loads`
