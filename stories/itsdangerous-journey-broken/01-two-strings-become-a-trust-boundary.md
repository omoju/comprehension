# Chapter 1 · Two Strings Become a Trust Boundary

> **I arrive as:** the arguments to `URLSafeSerializer("secret key", "auth")` — two ordinary Python `str` objects, `"secret key"` and `"auth"`.

I begin as two strings in the application's source, and by the end of this chapter I am no longer strings at all: I am the configuration of a trust boundary. Everything the rest of this story is allowed to guarantee is decided here, in one constructor, before a single byte of the user's identity is touched.

`URLSafeSerializer` itself has no body — it is [a class that only mixes two parents together](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L72-L76), `URLSafeSerializerMixin` and `Serializer[str]`. So the `__init__` that receives me is [`Serializer.__init__`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L190-L202). (The long stack of `@t.overload` declarations above it is for type checkers only; none of them run.)

## The secret key becomes a list

The first thing that happens to `"secret key"` is that it is handed to [`_make_keys_list`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L208-L208), which [asks one question: am I a `str` or `bytes`, or am I an iterable of them?](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L67-L73) I am a single `str`, so I am wrapped: `[want_bytes("secret key")]` → `[b'secret key']`.

That wrapping matters more than it looks. From this line onward there is no "single key" case in the library — there is only a list, oldest to newest. The key-rotation feature and the ordinary one-key deployment are literally the same code path; rotation costs nothing extra to support because nothing downstream knows the difference. Had I been given as `["old", "new"]`, I would have arrived here as a two-element list instead, and the story would continue unchanged.

The encoding step is [`want_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17): a `str` is UTF-8 encoded, `bytes` pass through untouched. Note what does *not* happen: there is no PBKDF2, no scrypt, no stretching of any kind. My bytes will be used more or less verbatim as HMAC key material. This is a deliberate design choice with a consequence an owner should be able to state out loud — *the secret key must be a long random value, not a password*, because nothing in this library will compensate for a weak one. The docs say exactly this and [recommend `os.urandom`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L20-L53).

## The salt becomes bytes, and stays visible

`"auth"` is handled next. The parameter [defaults to `b"itsdangerous"`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L193-L193), so passing `"auth"` replaces that default; it is [converted to bytes only if it isn't `None`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L210-L214), and `None` is a supported value meaning "let the `Signer` use its own default". I become `self.salt = b'auth'`.

I am not secret. I sit in the source file, and I will never be hidden from anyone. What I actually do is left for Chapter 3 — but it is worth flagging now as an open question for the reviewer: *what does a non-secret, source-visible salt buy?* And a second one, since nothing so far has mentioned encryption: *will the user's id and name be readable by whoever holds the finished token?*

## The serializer is chosen, then interrogated

`serializer` was not passed, so [the class attribute is used](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L216-L219). On a plain `Serializer` that would be [the stdlib `json` module](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L92-L95), but the URL-safe mixin comes first in the MRO and [overrides it with `_CompactJSON`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/url_safe.py#L15-L21). `_CompactJSON` is a thin wrapper that [sets `ensure_ascii=False` and `separators=(",", ":")`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/_json.py#L14-L18) — smaller output, same plain JSON content. It is still JSON, not pickle: a token's payload will be parsed by `json.loads`, which cannot execute anything.

Then comes the one line here that actually *runs* code rather than storing it: [`self.is_text_serializer = is_text_serializer(serializer)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L220-L220). [That function serializes an empty dict and checks whether the result is a `str`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L33-L37). `_CompactJSON.dumps({})` returns `"{}"`, a `str`, so my flag is `True`. It is an empirical test, done once, cached: later it will decide both whether `dumps` hands back `str` instead of `bytes` and whether a returning payload gets UTF-8 decoded before parsing. A custom serializer that returned `bytes` would flip this single boolean and both behaviours with it.

## The signer, and the list that is empty

`signer` was not passed either, so [the default class is taken](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L222-L226) — [`Signer`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L97-L99), the plain one with no timestamp. Nothing here will expire a token; that is `URLSafeTimedSerializer`'s job, not mine. `signer_kwargs` and `serializer_kwargs` both become `{}` via `or {}`.

Finally, `fallback_signers` is `None`, so I take [a copy of the class default](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L228-L233) — and [that default is an empty list](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/serializer.py#L101-L104). It was not always: version 2.0 removed the SHA-512 fallback that used to live there, [as the changelog records](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L95-L96). The practical effect is that exactly one signer configuration will be tried when a token comes back. No silent acceptance of tokens signed under parameters I was never told about.

I am fully assembled. Two strings went in; a policy came out.

> **I leave as:** a configured `URLSafeSerializer` — `secret_keys=[b'secret key']`, `salt=b'auth'`, `serializer=_CompactJSON`, `is_text_serializer=True`, `signer=Signer`, `signer_kwargs={}`, `serializer_kwargs={}`, `fallback_signers=[]`.

```python proof
from itsdangerous import URLSafeSerializer
from itsdangerous._json import _CompactJSON
from itsdangerous.serializer import is_text_serializer
from itsdangerous.signer import Signer

auth_s = URLSafeSerializer("secret key", "auth")

# _make_keys_list wrapped the single str key into a one-element list of bytes.
assert auth_s.secret_keys == [b"secret key"]
assert auth_s.secret_key == b"secret key"

# The salt was want_bytes'd, replacing the b"itsdangerous" default.
assert auth_s.salt == b"auth"
assert URLSafeSerializer("secret key").salt == b"itsdangerous"

# The URL-safe mixin's default serializer wins over stdlib json.
assert auth_s.serializer is _CompactJSON
assert _CompactJSON.dumps({}) == "{}"
assert is_text_serializer(_CompactJSON) is True
assert auth_s.is_text_serializer is True

# Plain Signer, no timestamp, no extra kwargs, and no fallback signers at all.
assert auth_s.signer is Signer
assert auth_s.signer_kwargs == {}
assert auth_s.serializer_kwargs == {}
assert auth_s.fallback_signers == []
assert URLSafeSerializer.default_fallback_signers == []

# The same constructor accepts a key list for rotation, oldest to newest.
assert URLSafeSerializer(["old", "new"], "auth").secret_keys == [b"old", b"new"]
```
