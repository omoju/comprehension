"""Replays the scenario up to the end of chapter 3: the Request is built,
but not yet sent."""

import httpx
from httpx._content import ByteStream


def app(environ, start_response):  # never called in this proof
    raise AssertionError("the transport is not exercised in chapter 3")


transport = httpx.WSGITransport(app=app)

with httpx.Client(transport=transport, base_url="http://testserver") as client:
    # --- the two merges that decline to do anything (trace 162-173) ---
    assert client._merge_cookies(None) is None
    assert client._merge_queryparams(None) is None

    # --- the header merge (trace 136-161) ---
    merged = client._merge_headers({"X-Custom": "value"})
    assert merged["x-custom"] == "value"          # case-insensitive lookup
    assert merged["accept"] == "*/*"              # client default survives
    assert client.headers.get("x-custom") is None  # client itself untouched

    # --- the request itself (trace 178-246) ---
    request = client.build_request("GET", "/", headers={"X-Custom": "value"})

    assert repr(request) == "<Request('GET', 'http://testserver/')>"
    assert request.method == "GET"
    assert str(request.url) == "http://testserver/"

    # Host is auto-added and lands first; caller order is otherwise preserved.
    assert [key for key, _ in request.headers.raw] == [
        b"Host",
        b"Accept",
        b"Accept-Encoding",
        b"Connection",
        b"User-Agent",
        b"X-Custom",
    ]
    assert request.headers.raw[0] == (b"Host", b"testserver")
    assert request.headers.raw[-1] == (b"X-Custom", b"value")
    assert request.headers["accept-encoding"].startswith("gzip, deflate")
    assert request.headers["user-agent"].startswith("python-httpx/")

    # A GET with no body gets neither content header.
    assert "Content-Length" not in request.headers
    assert "Content-Type" not in request.headers
    # ...and no Cookie header was built, since the jar is empty.
    assert "Cookie" not in request.headers

    # The timeout travels inside the request as a plain dict.
    assert request.extensions == {
        "timeout": {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}
    }

    # An empty ByteStream body, already read into memory.
    assert isinstance(request.stream, ByteStream)
    assert request.content == b""
    assert request.read() == b""

    # A caller-supplied extensions['timeout'] suppresses the client default.
    override = client.build_request(
        "GET", "/", extensions={"timeout": {"connect": 1.0}}
    )
    assert override.extensions == {"timeout": {"connect": 1.0}}

    # update() replaces a same-named header rather than duplicating it.
    replaced = client.build_request("GET", "/", headers={"user-agent": "mine/1"})
    assert replaced.headers.get_list("user-agent") == ["mine/1"]

    # POST is the case that does get an auto Content-Length.
    posted = client.build_request("POST", "/")
    assert posted.headers["Content-Length"] == "0"

print("chapter 3 proof OK")
