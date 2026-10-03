"""Replay the scenario up to the point where the transport is about to be called."""

import time

import httpx
from httpx._auth import Auth, BasicAuth
from httpx._client import USE_CLIENT_DEFAULT, ClientState, UseClientDefault
from httpx._content import ByteStream
from httpx._types import SyncByteStream


def app(environ, start_response):  # never called in this proof
    raise AssertionError("the transport is not reached in chapter 4")


transport = httpx.WSGITransport(app=app)
client = httpx.Client(transport=transport, base_url="http://testserver")

# Chapter 1: lifecycle and wiring.
assert client._state is ClientState.UNOPENED
with client:
    assert client._state is ClientState.OPENED

    # Chapters 2-3: the request as it enters send().
    request = client.build_request("GET", "/", headers={"X-Custom": "value"})
    assert str(request.url) == "http://testserver/"
    assert request.extensions == {
        "timeout": {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}
    }

    # send(): the CLOSED gate passes, and follow_redirects resolves off the client.
    assert isinstance(USE_CLIENT_DEFAULT, UseClientDefault)
    assert client.follow_redirects is False
    assert client.max_redirects == 20

    # _set_timeout is a no-op: 'timeout' is already in extensions.
    before = dict(request.extensions)
    client._set_timeout(request)
    assert request.extensions == before

    # _build_request_auth: no client auth, no userinfo -> a bare Auth().
    assert client._auth is None
    assert request.url.username == ""
    assert request.url.password == ""
    auth = client._build_request_auth(request, USE_CLIENT_DEFAULT)
    assert type(auth) is Auth
    assert auth.requires_request_body is False
    assert auth.requires_response_body is False

    # The road not taken: userinfo in the URL becomes Basic auth with no opt-in.
    cred_request = client.build_request("GET", "http://user:pass@testserver/")
    assert cred_request.url.username == "user"
    cred_auth = client._build_request_auth(cred_request, USE_CLIENT_DEFAULT)
    assert isinstance(cred_auth, BasicAuth)

    # _send_handling_auth: next(flow) yields the very same request object.
    flow = auth.sync_auth_flow(request)
    first = next(flow)
    assert first is request
    flow.close()

    # _send_single_request: transport selection and the sync-stream guard.
    assert client._mounts == {}
    assert client._transport_for_url(request.url) is transport
    assert client._transport_for_url(httpx.URL("https://elsewhere.example")) is transport
    start = time.perf_counter()
    assert isinstance(request.stream, SyncByteStream)
    assert isinstance(request.stream, ByteStream)  # replayable on retry
    assert start > 0.0

# After the `with` block the gate is shut, one way.
assert client._state is ClientState.CLOSED
try:
    client.send(request)
except RuntimeError as exc:
    assert str(exc) == "Cannot send a request, as the client has been closed."
else:  # pragma: no cover
    raise AssertionError("expected RuntimeError on a closed client")
