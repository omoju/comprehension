"""Replays the scenario up to the end of chapter 6's span.

Chapter 6 covers trace lines 304-363: everything _send_single_request does to
the Response after the transport returns, plus the unwinding of the redirect
and auth loops. We stop just before Client.send() calls response.read().
"""

import httpx
from httpx._client import BoundSyncStream, ClientState, UseClientDefault
from httpx._transports.wsgi import WSGIByteStream
from httpx._types import SyncByteStream


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
    request = client.build_request("GET", "/", headers={"X-Custom": "value"})

    # --- The state as chapter 6 begins: what the transport handed back. ------
    raw_response = transport.handle_request(request)
    assert raw_response.status_code == 200
    assert isinstance(raw_response.stream, WSGIByteStream)
    assert isinstance(raw_response.stream, SyncByteStream)  # the assert at _client.py:1016
    assert raw_response._request is None                    # no request attached yet
    assert raw_response.extensions == {}                    # no http_version/reason_phrase
    assert not hasattr(raw_response, "_content")            # body unread

    # Missing extensions degrade gracefully, exactly as the log line found them.
    assert raw_response.http_version == "HTTP/1.1"
    assert raw_response.reason_phrase == "OK"

    # --- Now run the real span: _send_handling_auth -> ... -> dressed Response.
    client._set_timeout(request)
    auth = client._build_request_auth(request, UseClientDefault())
    response = client._send_handling_auth(
        request, auth=auth, follow_redirects=False, history=[]
    )

    # --- Dressing: request attached, stream wrapped, encoding policy set. ----
    assert response.request is request
    assert str(response.request.url) == "http://testserver/"
    assert isinstance(response.stream, BoundSyncStream)
    assert isinstance(response.stream._stream, WSGIByteStream)
    assert response.default_encoding == "utf-8"

    # Cookies were extracted into the *client's* jar; the app sent none.
    assert len(client.cookies.jar) == 0

    # --- The redirect loop did not loop, and set no next_request. -----------
    assert response.has_redirect_location is False
    assert response.history == []
    assert response.next_request is None

    # --- The body is still untouched as the response leaves chapter 6. ------
    assert not hasattr(response, "_content")
    assert response.is_closed is False
    assert response.is_stream_consumed is False

    # elapsed is only set on close, which has not happened yet.
    try:
        response.elapsed
    except RuntimeError as exc:
        assert "may only be accessed after the response" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError for unread .elapsed")

    assert client._state is ClientState.OPENED

    # Tidy up the stream we opened by calling the transport directly.
    raw_response.close()
    response.close()
