# Chapter 1 · Once upon a time, there was a message

> **Inputs:** none. This is where the world begins.
> **Code:** `encoding.py`, `signer.py` lines 15–173

Once upon a time, a server had to hand a message to a stranger.

The message was small: *this is user 42*, or *this link resets a password*. The stranger was a web browser, or an
email inbox, or anyone who happened to be holding the link. The server couldn't keep a copy of every message it
handed out, because there were too many and it had too little memory. So it handed the message over, forgot about
it, and hoped that one day the stranger would bring it back.

The trouble was that strangers can't be trusted. When the message came back saying *this is user 1*, how would the
server know whether that was what it wrote or something the stranger had scratched out and rewritten?

This is the problem `itsdangerous` exists to solve. It doesn't hide the message. Anyone can still read it. What it
does is make any change to the message *detectable*. To do that, it needs a small cast of characters.

## The translator

The first to arrive is the humblest. Her name is [`want_bytes`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L11-L17),
and she has one job: whatever you hand her, she hands back bytes. Give her text and she encodes it as UTF-8; give her
bytes and she passes them straight through. She is seven lines long, and nearly every other character in this story
calls on her before doing anything else. A signature is a mathematical thing and only works on bytes, so the first
act of any character here is to ask the translator to make sure they're holding bytes.

## The Signer and the secret

Next comes the hero, the [`Signer`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L76-L80).
A Signer is born holding a secret: a key that only the server knows. That key is the whole of the Signer's power.
Anyone could copy the Signer's methods. Nobody else holds its secret.

There is something odd about how the Signer holds its secret. Even if you give it exactly one key, it
[keeps a *list*](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L67-L73),
and the comments say it is ordered
[oldest to newest](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L138-L143).
Why would a hero with one secret keep a list of them? Remember that. It matters in chapter 3.

## The salt

The Signer also carries a salt, a second, public ingredient that gets mixed in with the secret. The salt is the
name of the *context*. A password-reset link and a login cookie might be signed with the same secret, but if they
use different salts, a signature made for one will never be accepted as the other. That way a stranger can't take
a cookie and pass it off as a reset link.

If you don't give the Signer a salt, it uses its own name,
[`b"itsdangerous.Signer"`](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L132).
Even if you *explicitly* say `salt=None`, it
[quietly uses the same default](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L153-L158).
It never goes without a salt.

## The separator, and the first rule of the world

Last comes the separator, the mark that will divide the message from its seal. By default it is
[a single dot](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L133).

And here the world gets its first law. When the Signer is born, it checks the separator against an
[alphabet](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/encoding.py#L41-L42):
every upper- and lower-case letter, every digit, and `-`, `_` and `=`. If the separator is one of those characters,
[the Signer refuses to exist](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L146-L151).
It raises a `ValueError` and no Signer is made.

Why should the separator be forbidden those characters in particular? The error message gives a hint, *"it may be
contained in the signature itself"*, but we haven't seen a signature yet. That's the question this chapter hands to
the next one.

## The quiet algorithm

Finally, since no one asked for anything else, the Signer is given its method:
[HMAC](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L170-L173),
over SHA-1. Even that has a small story. SHA-1 isn't looked up when the library loads; it's
[fetched only when first needed](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/src/itsdangerous/signer.py#L40-L45),
because some locked-down (FIPS) builds of Python don't include SHA-1 at all. If it were looked up at import time,
the library would crash before a developer had any chance to choose a different hash.

So the cast is assembled: a translator, a Signer, a list of secrets, a salt, a separator, and an algorithm. Nothing
has been signed yet.

---

### What this chapter hands to the next

| | |
|---|---|
| **Characters** | `want_bytes` · `Signer` · `secret_keys` · `salt` · `sep` · `HMACAlgorithm` |
| **Facts** | everything becomes bytes first · keys are a list, oldest → newest · salt defaults to `b"itsdangerous.Signer"`, even for `None` · `sep` defaults to `b"."` and can't be in the base64 alphabet · HMAC-SHA1 by default, and SHA-1 isn't looked up until it's used |
| **Open questions** | Why can't the separator be a letter? *(ch. 2)* · Why a list of keys? *(ch. 3)* |

### Proof

This block runs against the real repository. If the code stops matching the story, the chapter fails.

```python proof
from itsdangerous import Signer, want_bytes
from itsdangerous.signer import HMACAlgorithm

assert want_bytes("héllo") == "héllo".encode("utf-8")
assert want_bytes(b"raw") == b"raw"

s = Signer("my secret")
assert s.secret_keys == [b"my secret"]          # one key, still a list
assert s.salt == b"itsdangerous.Signer"
assert Signer("k", salt=None).salt == b"itsdangerous.Signer"
assert s.sep == b"."
assert isinstance(s.algorithm, HMACAlgorithm)

for bad in ["a", "Z", "7", "-", "_", "="]:
    try:
        Signer("k", sep=bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"separator {bad!r} should have been refused")

Signer("k", sep="|")                            # anything else is fine
```
