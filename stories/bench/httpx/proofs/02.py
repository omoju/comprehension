import httpx
from httpx._urlparse import urlparse

# --- The world of chapter 1, rebuilt. ---
def app(environ, start_response):  # never called in this chapter
    raise AssertionError("not reached")

transport = httpx.WSGITransport(app=app)
client = httpx.Client(transport=transport, base_url="http://testserver")

# The base URL carries the trailing slash guarantee from chapter 1.
assert client.base_url == httpx.URL("http://testserver")
assert client.base_url.raw_path == b"/"

# --- "/" parsed on its own terms. ---
parsed = urlparse("/")
assert parsed.scheme == ""
assert parsed.userinfo == ""
assert parsed.host == ""
assert parsed.port is None
assert parsed.path == "/"
assert parsed.query is None
assert parsed.fragment is None

standalone = httpx.URL("/")
assert standalone.is_absolute_url is False
assert standalone.is_relative_url is True
assert standalone.raw_path == b"/"

# --- The merge itself. ---
merged = client._merge_url("/")
assert isinstance(merged, httpx.URL)
assert str(merged) == "http://testserver/"
assert merged.scheme == "http"
assert merged.host == "testserver"
assert merged.port is None
assert merged.path == "/"
assert merged.query == b""
assert merged.raw_path == b"/"
assert merged._uri_reference.query is None  # no trailing "?" in the URL

# The merge appends to the base path; it never replaces it.
sub = httpx.Client(transport=transport, base_url="http://testserver/subpath")
assert sub.base_url.raw_path == b"/subpath/"
assert str(sub._merge_url("/path")) == "http://testserver/subpath/path"
assert str(sub._merge_url("path")) == "http://testserver/subpath/path"
sub.close()

# The road not taken: an absolute argument bypasses base_url entirely.
absolute = client._merge_url("http://evil.example.com/path")
assert str(absolute) == "http://evil.example.com/path"

# The guard on control characters in URLs.
try:
    httpx.URL("/bad\r\npath")
except httpx.InvalidURL as exc:
    assert "Invalid non-printable ASCII character" in str(exc)
else:  # pragma: no cover
    raise AssertionError("InvalidURL was not raised")

# InvalidURL is not an HTTPError, so a blanket handler would miss it.
assert not issubclass(httpx.InvalidURL, httpx.HTTPError)

client.close()
print("chapter 2 ok")
