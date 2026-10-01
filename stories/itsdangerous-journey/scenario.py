"""README example: sign a user's id and name into a URL-safe token and read it back."""

import os
import sys

# The package lives in src/; make it importable when run from the repo root.
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

from itsdangerous import URLSafeSerializer


def main() -> None:
    auth_s = URLSafeSerializer("secret key", "auth")

    user = {"id": 5, "name": "itsdangerous"}
    token = auth_s.dumps(user)
    print("token:", token)

    # The token is a URL-safe string: base64 payload, a dot, then the signature.
    assert isinstance(token, str)
    payload, sep, signature = token.partition(".")
    assert sep == "." and payload and signature
    assert payload == "eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9"

    # Hand the token to an untrusted environment and get it back safe and sound.
    data = auth_s.loads(token)
    print("name:", data["name"])

    assert data == user
    assert data["name"] == "itsdangerous"


if __name__ == "__main__":
    main()
