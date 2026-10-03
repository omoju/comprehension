import io
import httpx
from httpx._transports.wsgi import WSGIByteStream, _skip_leading_empty_chunks

seen_environ = {}


def app(environ, start_response):
    seen_environ.update(environ)
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
client = httpx.Client(transport=transport, base_url="http://testserver")

# Rebuild exactly the request that entered this chapter's span.
request = client.build_request("GET", "/", headers={"X-Custom": "value"})
assert str(request.url) == "http://testserver/"
assert request.headers.raw == [
    (b"Host", b"testserver"),
    (b"Accept", b"*/*"),
    (b"Accept-Encoding", b"gzip, deflate"),
    (b"Connection", b"keep-alive"),
    (b"User-Agent", b"python-httpx/0.28.1"),
    (b"X-Custom", b"value"),
]
assert request.content == b""
assert request.extensions["timeout"] == {
    "connect": 5.0,
    "read": 5.0,
    "write": 5.0,
    "pool": 5.0,
}

# The chapter's span: handle_request, called directly.
response = transport.handle_request(request)

# The URL was flattened into the environ; the port came from the scheme table.
assert request.url.port is None
assert request.url.scheme == "http"
assert seen_environ["SERVER_PORT"] == "80"
assert seen_environ["REQUEST_METHOD"] == "GET"
assert seen_environ["PATH_INFO"] == "/"
assert seen_environ["QUERY_STRING"] == ""
assert seen_environ["SERVER_NAME"] == "testserver"
assert seen_environ["SCRIPT_NAME"] == ""
assert seen_environ["REMOTE_ADDR"] == "127.0.0.1"
assert seen_environ["SERVER_PROTOCOL"] == "HTTP/1.1"

# The caller's header crossed the boundary with the WSGI name mangling applied.
assert seen_environ["HTTP_X_CUSTOM"] == "value"
assert seen_environ["HTTP_HOST"] == "testserver"
assert isinstance(seen_environ["wsgi.input"], io.BytesIO)
assert seen_environ["wsgi.input"].getvalue() == b""

# The timeout extension was never consulted by this transport.
assert "timeout" not in {k.lower() for k in seen_environ}

# What came back out of handle_request.
assert response.status_code == 200
assert response.headers.raw == [
    (b"Content-Type", b"text/plain; charset=utf-8"),
    (b"Content-Length", b"12"),
]
assert isinstance(response.stream, WSGIByteStream)
assert response.extensions == {}
assert response._request is None
assert not hasattr(response, "_content")  # stream=... skips the eager read

# A plain list exposes no close(); that is why _close is None here.
assert response.stream._close is None

# Leading empty chunks are dropped before the body is exposed.
assert list(_skip_leading_empty_chunks([b"", b"", b"real"])) == [b"real"]
assert list(_skip_leading_empty_chunks([])) == []

# An app that never calls start_response trips a bare AssertionError,
# not an httpx exception.
def silent_app(environ, start_response):
    return [b""]


try:
    httpx.WSGITransport(app=silent_app).handle_request(
        client.build_request("GET", "/")
    )
except AssertionError:
    pass
else:  # pragma: no cover
    raise SystemExit("expected AssertionError")

# raise_app_exceptions=True re-raises the app's own exception type.
class Boom(Exception):
    pass


def failing_app(environ, start_response):
    try:
        raise Boom("app blew up")
    except Boom:
        import sys

        start_response("500 Internal Server Error", [], sys.exc_info())
        return [b""]


try:
    httpx.WSGITransport(app=failing_app).handle_request(
        client.build_request("GET", "/")
    )
except Boom:
    pass
else:  # pragma: no cover
    raise SystemExit("expected Boom")

# ...and raise_app_exceptions=False hands back the 500 instead.
quiet = httpx.WSGITransport(app=failing_app, raise_app_exceptions=False)
assert quiet.handle_request(client.build_request("GET", "/")).status_code == 500

client.close()
print("ok")
