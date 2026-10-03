"""Replay the scenario through the end of chapter 7: the body is read,
the stream is consumed and closed, and `elapsed` has been stamped."""

import datetime

import httpx
from httpx._decoders import IdentityDecoder


closed_app_iterables = []


class ClosableBody:
    """A WSGI iterable that records when the transport closes it."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)

    def close(self):
        closed_app_iterables.append(self)


def app(environ, start_response):
    assert environ["REQUEST_METHOD"] == "GET"
    assert environ["PATH_INFO"] == "/"
    assert environ["HTTP_X_CUSTOM"] == "value"

    body = b"Hello World!"
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return ClosableBody([body])


transport = httpx.WSGITransport(app=app)

with httpx.Client(transport=transport, base_url="http://testserver") as client:
    # --- Chapters 1-6: everything up to the body being read. ---
    request = client.build_request("GET", "/", headers={"X-Custom": "value"})
    assert str(request.url) == "http://testserver/"
    assert request.headers["X-Custom"] == "value"

    # Send with stream=True so we can inspect the response *before* chapter 7's
    # read() happens -- this is exactly the state chapter 7 opens on.
    response = client.send(request, stream=True)

    assert response.status_code == 200
    assert response.request is request
    assert response.history == []
    assert response.next_request is None
    assert response.http_version == "HTTP/1.1"      # fallback, not from the app
    assert response.reason_phrase == "OK"           # fallback, from codes table
    assert response.default_encoding == "utf-8"
    assert not hasattr(response, "_content")
    assert response.is_stream_consumed is False
    assert response.is_closed is False

    # `elapsed` is not available until the stream is closed.
    try:
        response.elapsed
    except RuntimeError as exc:
        assert "may only be accessed after the response" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError for unread .elapsed")

    # The app sent no Content-Encoding, so an IdentityDecoder is selected.
    assert response.headers.get_list("content-encoding", split_commas=True) == []
    assert isinstance(response._get_content_decoder(), IdentityDecoder)

    # --- Chapter 7: the read itself. ---
    content = response.read()

    assert content == b"Hello World!"
    assert response.content == b"Hello World!"
    assert response.num_bytes_downloaded == 12      # raw, pre-decode bytes
    assert response.is_stream_consumed is True
    assert response.is_closed is True

    # close() ran: BoundSyncStream stamped elapsed, and the app iterable's
    # own close() was invoked via WSGIByteStream.close().
    assert isinstance(response.elapsed, datetime.timedelta)
    assert response.elapsed.total_seconds() >= 0.0
    assert len(closed_app_iterables) == 1

    # The three refusals in iter_raw(): the stream cannot be read again.
    try:
        list(response.iter_raw())
    except httpx.StreamConsumed:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected StreamConsumed on a second iter_raw()")

    # But read() is idempotent, because _content is cached.
    assert response.read() == b"Hello World!"

print("chapter 7 proof ok")
