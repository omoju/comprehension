# Chapter 4 · Keys, Salts, and the Choice of Algorithm

> **Inputs:** `want_bytes` and the bytes-only world below it (ch. 2) · `BadSignature` and the rule that failures are typed exceptions (ch. 3) · chapter 1's claim that the whole guarantee rests on one input, `secret_key`.
> **Code:** `src/itsdangerous/signer.py` lines 15–73 and 113–173, `derive_key` at 182–213, and `docs/concepts.rst` "The Salt".

Chapter 1 said the security of every token comes down to `secret_key`. That is true, but it is not the whole configuration. Before a single byte gets signed, a `Signer` has to answer four questions: *which* key, mixed with *what* context, stirred by *which* derivation scheme, under *which* algorithm. All four are constructor arguments. Three of them have defaults you will want to have an opinion about, and two of them have settings that switch the guarantee off entirely.

This chapter is the configuration surface. Chapter 5 is what it does.

## The key is always a list

The first thing the constructor does is [normalise the secret key into a list of byte strings](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L138-L143), through a four-line helper:

```python
def _make_keys_list(secret_key): ...
```

[`_make_keys_list`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L67-L73) special-cases `str` and `bytes` and wraps them in a one-element list; anything else it treats as an iterable and runs each element through `want_bytes`. So `Signer("ab")` holds one key `b"ab"`, not two keys `b"a"` and `b"b"` — the isinstance check exists precisely to stop a string being iterated character by character.

The list is ordered **oldest to newest**, as [the attribute comment says](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L138-L143), and the [`secret_key` property](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L175-L180) is just `secret_keys[-1]`, kept for compatibility from before [key rotation was added in 2.0](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L92-L94). That ordering is a contract your operations team has to honour: [the docs describe the rotation procedure](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L101-L120) as append-the-new, drop-the-oldest, and say plainly that generating and maintaining that list is *outside the scope of ItsDangerous*. Which key signs and which keys verify is **q4.1**, and chapter 5 answers it.

Two things the constructor does *not* do: check that the list is non-empty, or check that the keys are any good. `Signer([])` is built happily and blows up with a bare `IndexError` the first time it tries to derive a key — a misconfiguration that surfaces at the first signature rather than at startup. And nothing enforces the docs' advice that the key be ["a long random string of bytes"](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L18-L29). `Signer("password")` works.

## The salt is a context name, not a cryptographic salt

The second argument [defaults to `b"itsdangerous.Signer"`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L153-L158), and passing `salt=None` explicitly gets you the same default — there is no way to have no salt.

Despite the name, this is not a defence against rainbow tables. It is a **context label**, and [the docs are explicit](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L56-L69): it "doesn't have to be random, and can be saved in code. It only has to be unique between contexts, not private." The worked example is the one that matters to an owner — [an account-activation link and an account-upgrade link](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/concepts.rst#L64-L92) that both sign nothing but a user id. Same key, same payload, different salts: the tokens are not interchangeable. Same key, same payload, *same* salt: a user who is entitled to one is entitled to the other.

That makes "are salts distinct per context?" a review question, not a style preference. There is no mechanism that detects two contexts sharing a salt; it fails silently, in the direction of accepting things.

## How the salt actually enters: `derive_key`

The salt is never part of the signed message. It is folded into the **key**, by [`derive_key`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L182-L213), and the docstring opens with a warning worth quoting:

> *Key derivation is not intended to be used as a security method to make a complex key out of a short password. Instead you should use large random secret keys.*

This is one hash invocation, not PBKDF2. A weak secret key is not stretched into a strong one.

There are four schemes:

| `key_derivation` | derived key |
|---|---|
| `"concat"` | [`digest(salt + secret_key)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L200-L201) |
| `"django-concat"` *(default)* | [`digest(salt + b"signer" + secret_key)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L202-L205) |
| `"hmac"` | [`HMAC(secret_key, salt)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L206-L209) |
| `"none"` | [the raw secret key, unchanged](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L210-L211) |

The default is [`"django-concat"`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L122-L127), inherited from Django's session signing.

Three observations for the person signing off.

**`"none"` disables context separation.** It returns the secret key and never touches the salt, so two signers with different salts produce byte-identical tokens. Everything the previous section promised about activation-versus-upgrade evaporates. It is also **undocumented**: both [the constructor docstring](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L90-L93) and [the class attribute comment](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L122-L127) list only `concat`, `django-concat` and `hmac`. The code accepts a fourth value that the documentation does not mention, and [the test suite exercises it](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/tests/test_itsdangerous/test_signer.py#L67-L72), so it is supported in fact if not in prose.

**A typo is accepted and fails late.** The constructor [stores whatever string you give it](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L160-L163) without validation; the [`raise TypeError("Unknown key derivation method")`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L212-L213) only fires the first time a key is derived — i.e. at the first sign or verify, in a request, not at boot. And note from chapter 3 that this `TypeError` is not a `BadData`: it will sail straight through `except BadSignature` and out of `validate`.

**The concatenating schemes have no length delimiter.** `salt + secret_key` means the derived key is a function of the *concatenation*, so the pair `(salt=b"a", key=b"bc")` and the pair `(salt=b"ab", key=b"c")` derive the same key. With a fixed key list this is harmless — distinct salts still give distinct keys. It only becomes interesting if salts are ever computed from untrusted input in a system that also varies keys. Worth knowing; not worth losing sleep over.

## The algorithm object

Below the key derivation sits a small strategy object. [`SigningAlgorithm`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L15-L28) is the contract: subclasses must implement [`get_signature`, which otherwise raises `NotImplementedError`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L20-L22), and they inherit a [`verify_signature` that recomputes the signature and compares with `hmac.compare_digest`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L24-L28).

That default matters twice over. First, **signature comparison is constant-time out of the box** — no `==` on secrets, no byte-by-byte early exit for an attacker to time. Second, it bakes in an assumption: verification means *re-derive the expected tag and compare*. That is only true for symmetric MACs. Anyone plugging in an asymmetric scheme must override `verify_signature` as well as `get_signature`, or they will be trying to sign with a public key. The base class does not stop them.

[`HMACAlgorithm`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L48-L64) is the real one: `hmac.new(key, msg=value, digestmod=self.digest_method).digest()`.

[`NoneAlgorithm`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L31-L37) returns `b""`. Every signature is the empty string; every empty string compares equal to every empty string; **every token verifies**. It is not hidden — it is [exported from the package root](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/__init__.py#L11-L13) and [has its own entry in the public docs](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/docs/signer.rst#L44-L49) with no warning attached. Presumably it exists for testing and for symmetry with the strategy pattern (that is my reading; the code says nothing about intent). Either way, `algorithm=NoneAlgorithm()` anywhere outside a test is a total authentication bypass, and it is one keyword argument away.

One more sharp edge in the same constructor block. `digest_method` and `algorithm` overlap: the signer [stores `digest_method`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L165-L168) and then [only builds an `HMACAlgorithm` from it if you didn't supply an `algorithm`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L170-L173). Pass both, and your `digest_method` still governs *key derivation* but is silently ignored for the *MAC* — a hybrid nobody asked for, with no warning. The test suite quietly acknowledges the split by only asserting the two agree [when `algorithm is None`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/tests/test_itsdangerous/test_signer.py#L84-L92).

## SHA-1, and why it isn't imported

The default digest is [`_lazy_sha1`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L40-L45), referenced as the default on [both `Signer`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L114-L120) and [`HMACAlgorithm`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L51-L54). It is a one-line wrapper whose only purpose is deferral, and its docstring explains why: FIPS builds may not ship SHA-1, and a module-level `hashlib.sha1` reference would blow up at import time — *before the developer can configure something else*. That is [the 2.2.0 changelog entry](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/CHANGES.rst#L25-L27) made flesh.

Which leaves the question a security reviewer will ask first: **SHA-1, in 2025, as the default?** That's **q4.2**, and it has a real answer, in the docs, with a real counter-argument. Chapter 10 gives it.

---

So: **q1.1**, from chapter 1, is now answerable. The signature is computed over the **value bytes only** — [`algorithm.get_signature(derive_key(), value)`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L215-L220). The salt is not in the message; it is in the key. That is why a token signed for `"activate"` fails under `"upgrade"`: not because the verifier notices a mismatched label, but because it derives a different key and the tag simply doesn't match. And it is why the token doesn't carry its own salt — the verifier must already know which context it is in.

---

### What this chapter hands to the next

| | |
|---|---|
| **Characters** | `_make_keys_list` · `Signer.secret_keys` / `.secret_key` · `salt` · `derive_key` · `SigningAlgorithm` · `HMACAlgorithm` · `NoneAlgorithm` · `_lazy_sha1` |
| **Facts** | keys are always a `list[bytes]`, oldest → newest; a `str`/`bytes` key is *not* iterated; an empty list builds fine and `IndexError`s later · salt defaults to `b"itsdangerous.Signer"`, `None` means the same, and it is a context label rather than a cryptographic salt · four derivations: `concat`, `django-concat` (default), `hmac`, and the undocumented `none`, which ignores the salt and destroys context separation · an unknown derivation string is accepted and raises `TypeError` only at first use — and `TypeError` is not a `BadData` · `derive_key` is one hash, explicitly *not* a password KDF · `SigningAlgorithm.verify_signature` compares with `hmac.compare_digest` (constant time) and assumes a symmetric recompute-and-compare · `NoneAlgorithm` makes every token verify and is publicly exported and documented · passing both `algorithm=` and `digest_method=` silently applies the digest only to key derivation · SHA-1 is the default digest, looked up lazily for FIPS builds |
| **Answered** | *q1.1* — the HMAC covers the value bytes only, keyed by `derive_key(secret_key, salt)`. Context separation comes from the derived key, not from anything inside the message; the token does not carry its salt. |
| **Open questions** | *q4.1* Which key signs, and are all of them tried on verify, in what order? *(ch. 5)* · *q4.2* Is SHA-1 as the 2025 default defensible or a finding? *(ch. 10)* |

### Proof

Runs from the repository root with `PYTHONPATH=src`.

```python proof
import hashlib
import hmac
import inspect
import pathlib

import itsdangerous
from itsdangerous.encoding import base64_encode
from itsdangerous.exc import BadSignature
from itsdangerous.signer import (
    HMACAlgorithm,
    NoneAlgorithm,
    Signer,
    SigningAlgorithm,
    _lazy_sha1,
    _make_keys_list,
)

# --- The key is always a list, oldest -> newest. ---
assert _make_keys_list("a") == [b"a"]
assert _make_keys_list(b"a") == [b"a"]
assert _make_keys_list(["old", "new"]) == [b"old", b"new"]
assert _make_keys_list(iter([b"old", "new"])) == [b"old", b"new"]
assert Signer("ab").secret_keys == [b"ab"]          # a str is NOT iterated char by char
assert Signer(["old", "new"]).secret_keys == [b"old", b"new"]
assert Signer(["old", "new"]).secret_key == b"new"  # the property is [-1]

# An empty list is accepted by the constructor and fails later, not at startup.
empty = Signer([])
assert empty.secret_keys == []
try:
    empty.derive_key()
except IndexError:
    pass
else:
    raise AssertionError("an empty key list must not silently derive a key")

# --- The salt: default, None, and context separation. ---
assert Signer("k").salt == b"itsdangerous.Signer"
assert Signer("k", salt=None).salt == b"itsdangerous.Signer"
assert Signer("k", salt="activate").salt == b"activate"

activate = Signer("secret-key", salt="activate")
upgrade = Signer("secret-key", salt="upgrade")
token = activate.sign(b"42")
assert upgrade.sign(b"42") != token
assert activate.unsign(token) == b"42"
try:
    upgrade.unsign(token)
except BadSignature:
    pass
else:
    raise AssertionError("a token from one salt must not verify under another")

# --- What is actually signed: the value bytes, under the derived key. ---
key = activate.derive_key()
expected = base64_encode(hmac.new(key, b"42", digestmod=hashlib.sha1).digest())
assert activate.get_signature(b"42") == expected
assert token == b"42." + expected           # salt is in the key, not in the message

# --- The four derivation schemes, exactly. ---
salt, secret = b"the-salt", b"the-key"
assert Signer.default_key_derivation == "django-concat"

concat = Signer(secret, salt=salt, key_derivation="concat")
django = Signer(secret, salt=salt, key_derivation="django-concat")
machmac = Signer(secret, salt=salt, key_derivation="hmac")
noderiv = Signer(secret, salt=salt, key_derivation="none")

assert concat.derive_key() == hashlib.sha1(salt + secret).digest()
assert django.derive_key() == hashlib.sha1(salt + b"signer" + secret).digest()
m = hmac.new(secret, digestmod=hashlib.sha1)
m.update(salt)
assert machmac.derive_key() == m.digest()
assert noderiv.derive_key() == secret                       # raw key, salt untouched
assert Signer(secret, salt=salt).derive_key() == django.derive_key()  # the default

# "none" throws away the context separation the salt exists for.
other = Signer(secret, salt=b"completely-different", key_derivation="none")
assert other.sign(b"42") == noderiv.sign(b"42")

# ...and it is documented nowhere.
doc = inspect.getdoc(Signer)
assert "``concat``" in doc and "``django-concat``" in doc and "``hmac``" in doc
assert "``none``" not in doc

# No length delimiter: distinct (salt, key) pairs can derive the same key.
assert (
    Signer(b"bc", salt=b"a", key_derivation="concat").derive_key()
    == Signer(b"c", salt=b"ab", key_derivation="concat").derive_key()
)

# An unknown scheme is accepted at construction and only fails when used,
# with a TypeError that is NOT a library BadData error.
typo = Signer("k", key_derivation="pbkdf2")
assert typo.key_derivation == "pbkdf2"
try:
    typo.derive_key()
except TypeError as e:
    assert not isinstance(e, itsdangerous.BadData)
else:
    raise AssertionError("an unknown key derivation must raise TypeError")

# --- The algorithm object. ---
assert isinstance(Signer("k").algorithm, HMACAlgorithm)
try:
    SigningAlgorithm().get_signature(b"k", b"v")
except NotImplementedError:
    pass
else:
    raise AssertionError("the abstract algorithm must refuse to sign")

# Verification is constant-time, and every subclass inherits that same method.
assert "compare_digest" in inspect.getsource(SigningAlgorithm.verify_signature)
assert HMACAlgorithm.verify_signature is SigningAlgorithm.verify_signature
assert NoneAlgorithm.verify_signature is SigningAlgorithm.verify_signature

# --- NoneAlgorithm: a total bypass, one keyword argument away. ---
bypass = Signer("secret-key", algorithm=NoneAlgorithm())
assert bypass.get_signature(b"anything") == b""
assert bypass.sign(b"user=42") == b"user=42."
assert bypass.unsign(b"user=1.") == b"user=1"        # forged, and accepted
assert bypass.validate(b"i-made-this-up.") is True
assert itsdangerous.NoneAlgorithm is NoneAlgorithm    # publicly exported
assert "NoneAlgorithm" in pathlib.Path("docs/signer.rst").read_text()

# --- algorithm= silently wins over digest_method= for the MAC. ---
hybrid = Signer("k", digest_method=hashlib.sha512, algorithm=HMACAlgorithm())
assert hybrid.digest_method is hashlib.sha512
assert hybrid.algorithm.digest_method is _lazy_sha1
assert len(hybrid.algorithm.get_signature(b"key", b"v")) == 20   # SHA-1 sized MAC
assert len(Signer("k", digest_method=hashlib.sha512).algorithm
           .get_signature(b"key", b"v")) == 64                   # SHA-512 sized MAC
# ...yet the sha512 still governs key derivation: a hybrid nobody asked for.
assert hybrid.derive_key() == hashlib.sha512(hybrid.salt + b"signer" + b"k").digest()

# --- SHA-1 by default, and never looked up at import time. ---
assert Signer.default_digest_method is _lazy_sha1
assert HMACAlgorithm.default_digest_method is _lazy_sha1
assert _lazy_sha1(b"abc").hexdigest() == hashlib.sha1(b"abc").hexdigest()
src = pathlib.Path("src/itsdangerous/signer.py").read_text()
assert src.count("hashlib.sha1(") == 1                       # only inside _lazy_sha1
assert "hashlib.sha1(string)" in inspect.getsource(_lazy_sha1)
```
