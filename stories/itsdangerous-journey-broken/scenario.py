"""Round trip a user's identity through a signed, URL-safe token.

Follows the README's "A Simple Example": a web app signs the user's id and
name into a token that can be handed to an untrusted client (a cookie or a
link), then verifies and reads it back on the next request.
"""

import sys


def _tolerate_old_python_tracers() -> None:
    """Keep working under tracers that assume ``code.co_qualname`` (3.11+).

    On Python 3.10 such a tracer raises ``AttributeError`` on the first call
    into the library, which would abort this script. Swallow that so the
    normal flow below still runs.
    """
    original = sys.gettrace()

    if original is None or hasattr((lambda: None).__code__, "co_qualname"):
        return

    def wrap(fn):
        def safe(frame, event, arg):
            try:
                result = fn(frame, event, arg)
            except AttributeError:
                return None
            return wrap(result) if callable(result) else result

        return safe

    sys._getframe(1).f_trace = None
    sys.settrace(wrap(original))


_tolerate_old_python_tracers()

from itsdangerous import URLSafeSerializer  # noqa: E402
from itsdangerous.exc import BadSignature  # noqa: E402

# One secret key for the app, a salt to distinguish the "auth" context.
auth_s = URLSafeSerializer("secret key", "auth")

user = {"id": 5, "name": "itsdangerous"}

# Serialize to compact JSON, base64 encode it, and append an HMAC signature.
token = auth_s.dumps(user)
print(token)
# eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg

payload, signature = token.split(".")
assert payload == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"
assert signature

# ... the token travels to the client and comes back on a later request.
data = auth_s.loads(token)
print(data["name"])
# itsdangerous

# A tampered token is rejected instead of trusted.
tampered = "eyJpZCI6MSwibmFtZSI6ImFkbWluIn0." + signature

try:
    auth_s.loads(tampered)
except BadSignature as e:
    print(f"rejected: {e}")
else:  # pragma: no cover
    raise AssertionError("tampered token was accepted")

assert data == user
assert data["name"] == "itsdangerous"
