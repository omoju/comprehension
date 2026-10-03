import datetime

import httpx
from httpx._client import ClientState


def app(environ, start_response):
    assert environ["REQUEST_METHOD"] == "GET"
    assert environ["PATH_INFO"] == "/"
    body = b"Hello World!"
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


transport = httpx.WSGITransport(app=app)

with httpx.Client(transport=transport, base_url="http://testserver") as client:
    response = client.get("/", headers={"X-Custom": "value"})

    # --- Chapter 8, trace lines 398-452 ---

    # repr: the reason phrase is reconstructed from the status-code table,
    # because the WSGI transport set no "reason_phrase" extension.
    assert "reason_phrase" not in response.extensions
    assert response.reason_phrase == "OK"
    assert repr(response) == "<Response [200 OK]>"

    # The request URL stringifies back to the normalised absolute form,
    # not the "/" the caller passed.
    assert str(response.request.url) == "http://testserver/"

    # Header lookup is case-insensitive; the Headers encoding sniffs to ascii.
    assert response.headers.encoding == "ascii"
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"

    # Encoding priority: the Content-Type charset wins, and it is a known codec.
    assert response.charset_encoding == "utf-8"
    assert response.default_encoding == "utf-8"
    assert response.encoding == "utf-8"

    # Text decoding of the buffered bytes.
    assert response.content == b"Hello World!"
    assert response.text == "Hello World!"

    # Once .text has been accessed, the encoding is locked.
    try:
        response.encoding = "latin-1"
    except ValueError as exc:
        assert "after `text` has been accessed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError when setting encoding after .text")

    # The request object is the record of what actually went out.
    assert response.request.headers["X-Custom"] == "value"
    assert response.status_code == 200

    # Still inside the block: the client is OPENED, mounts are empty.
    assert client._state is ClientState.OPENED
    assert client._mounts == {}
    assert client._transport is transport

    # elapsed was set when the stream closed, during send()'s read().
    assert isinstance(response.elapsed, datetime.timedelta)

# --- Exiting the with block, trace lines 453-458 ---

assert client._state is ClientState.CLOSED
assert client.is_closed is True

# Sending on a closed client is refused.
try:
    client.get("/")
except RuntimeError as exc:
    assert str(exc) == "Cannot send a request, as the client has been closed."
else:  # pragma: no cover
    raise AssertionError("expected RuntimeError after close")

# Reopening is refused too.
try:
    with client:
        pass  # pragma: no cover
except RuntimeError as exc:
    assert "Cannot reopen a client instance" in str(exc)
else:  # pragma: no cover
    raise AssertionError("expected RuntimeError on re-entering a closed client")

# WSGITransport inherits BaseTransport.close(), which does nothing;
# calling it again is harmless because it owns no resources.
assert type(transport).close is httpx.BaseTransport.close
transport.close()

# The buffered response outlives its client.
assert response.text == "Hello World!"
assert response.content == b"Hello World!"

print("chapter 8 proof ok")
