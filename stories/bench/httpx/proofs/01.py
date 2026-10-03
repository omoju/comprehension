"""Replays the scenario's setup (trace lines 2-75) and asserts the world
that the request is about to enter. Run from the repo root with PYTHONPATH=.
"""

import httpx
from httpx._client import ClientState
from httpx._decoders import SUPPORTED_DECODERS
from httpx.__version__ import __version__


def app(environ, start_response):  # never called in this chapter
    body = b"Hello World!"
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


# --- trace line 2: WSGITransport.__init__ -----------------------------------
transport = httpx.WSGITransport(app=app)
assert transport.app is app
assert transport.raise_app_exceptions is True
assert transport.script_name == ""
assert transport.remote_addr == "127.0.0.1"
assert transport.wsgi_errors is None

# --- trace line 4: Client.__init__ ------------------------------------------
client = httpx.Client(transport=transport, base_url="http://testserver")

# The caller's transport is used verbatim; no HTTPTransport was built.
assert client._transport is transport
assert not isinstance(client._transport, httpx.HTTPTransport)

# trust_env is True, but an explicit transport disabled env proxy lookup,
# so the mount table is empty and this transport will serve every URL.
assert client.trust_env is True
assert client._mounts == {}

# base_url parsed and left alone by _enforce_trailing_slash.
assert str(client.base_url) == "http://testserver"
assert client.base_url.raw_path == b"/"
assert client.base_url.scheme == "http"
assert client.base_url.host == "testserver"
assert client.base_url.port is None

# The four client-level default headers, in order.
assert list(client.headers.keys()) == [
    "accept",
    "accept-encoding",
    "connection",
    "user-agent",
]
assert client.headers["accept"] == "*/*"
expected_accept_encoding = ", ".join(
    key for key in SUPPORTED_DECODERS.keys() if key != "identity"
)
assert client.headers["accept-encoding"] == expected_accept_encoding
assert expected_accept_encoding.startswith("gzip, deflate")
assert client.headers["connection"] == "keep-alive"
assert client.headers["user-agent"] == f"python-httpx/{__version__}"

# Defaults that shape everything downstream.
assert client.timeout.as_dict() == {
    "connect": 5.0,
    "read": 5.0,
    "write": 5.0,
    "pool": 5.0,
}
assert client.follow_redirects is False
assert client.max_redirects == 20
assert client.event_hooks == {"request": [], "response": []}
assert client.auth is None
assert len(client.cookies) == 0
assert len(client.params) == 0

# Not opened yet.
assert client._state is ClientState.UNOPENED
assert client.is_closed is False

# --- trace line 72: Client.__enter__ ----------------------------------------
entered = client.__enter__()
assert entered is client
assert client._state is ClientState.OPENED

# Re-entering is refused, and leaves the state untouched.
try:
    client.__enter__()
except RuntimeError as exc:
    assert str(exc) == "Cannot open a client instance more than once."
else:
    raise AssertionError("expected RuntimeError on re-entering the client")
assert client._state is ClientState.OPENED

print("chapter 1 ok")
