"""Chapter 4: prepare_headers and prepare_cookies. Run from the repo root with PYTHONPATH=src."""

from requests.cookies import MockRequest, RequestsCookieJar, get_cookie_header
from requests.exceptions import InvalidHeader
from requests.models import PreparedRequest
from requests.structures import CaseInsensitiveDict
from requests.utils import check_header_validity

URL = "http://127.0.0.1:54897/basic-auth/user/pass"

# The merged headers as Chapter 2 produced them, in the trace's order.
merged = CaseInsensitiveDict(
    {
        "User-Agent": "python-requests/2.34.2",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }
)

p = PreparedRequest()
p.prepare_method("GET")
p.prepare_url(URL, {})
assert p.method == "GET"
assert p.url == URL
assert p.headers is None  # nothing stored yet (models.py:413)

# --- prepare_headers -------------------------------------------------------
p.prepare_headers(merged)
assert list(p.headers) == [
    "User-Agent",
    "Accept-Encoding",
    "Accept",
    "Connection",
]
assert p.headers["User-Agent"] == "python-requests/2.34.2"
assert p.headers["Accept-Encoding"] == "gzip, deflate"
assert p.headers["Accept"] == "*/*"
assert p.headers["Connection"] == "keep-alive"
# Casing is remembered, lookup is not case sensitive (structures.py:59-65).
assert p.headers["user-agent"] == "python-requests/2.34.2"

# The CRLF that never happens: validation rejects it before any socket opens.
for bad in [
    ("X-Thing", "ok\r\nX-Injected: yes"),
    ("X-Thing", "ok\nX-Injected: yes"),
    ("X-Thing\r\n", "ok"),
    ("X-Thing", " leading-space-is-rejected"),
    (":starts-with-colon", "ok"),
]:
    try:
        check_header_validity(bad)
    except InvalidHeader:
        pass
    else:
        raise AssertionError(f"expected InvalidHeader for {bad!r}")

# Non-str/bytes parts are rejected too, and bytes parts are accepted.
try:
    check_header_validity(("X-Thing", 1))  # type: ignore[arg-type]
except InvalidHeader:
    pass
else:
    raise AssertionError("expected InvalidHeader for a non-string header value")
assert check_header_validity((b"X-Thing", b"ok")) is None
assert check_header_validity(("X-Empty", "")) is None  # empty value allowed

# A bad value never reaches self.headers.
p_bad = PreparedRequest()
p_bad.prepare_method("GET")
p_bad.prepare_url(URL, {})
try:
    p_bad.prepare_headers({"X-Thing": "ok\r\nX-Injected: yes"})
except InvalidHeader:
    pass
else:
    raise AssertionError("prepare_headers accepted a CRLF value")
assert "X-Injected" not in p_bad.headers

# Keys differing only in case collapse into one entry.
cid = CaseInsensitiveDict()
cid["Accept"] = "a"
cid["ACCEPT"] = "b"
assert len(cid) == 1
assert list(cid) == ["ACCEPT"]
assert cid["accept"] == "b"

# --- prepare_cookies -------------------------------------------------------
jar = RequestsCookieJar()
assert list(jar) == []
p.prepare_cookies(jar)
assert p._cookies is jar  # an existing CookieJar is adopted, not rebuilt
assert "Cookie" not in p.headers
assert len(p.headers) == 4
assert get_cookie_header(jar, p) is None

# MockRequest is the adapter the stdlib cookie policy actually sees.
mr = MockRequest(p)
assert mr.get_type() == "http"
assert mr.get_host() == "127.0.0.1:54897"
assert mr.get_full_url() == URL
assert mr.is_unverifiable() is True
assert mr.get_new_headers() == {}

# A caller-set Host header changes the URL the cookie policy matches against.
p_host = p.copy()
p_host.headers["Host"] = "example.com"
assert MockRequest(p_host).get_full_url() == "http://example.com/basic-auth/user/pass"

# Body is still untouched at the end of this span.
assert p.body is None
print("chapter 4 ok")
