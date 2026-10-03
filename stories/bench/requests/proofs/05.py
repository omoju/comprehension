"""Replays the scenario's request preparation up to the end of Chapter 5.

Run from the repository root with PYTHONPATH=src.
No network is used: preparation is complete before any socket opens.
"""

from requests.auth import HTTPBasicAuth, _basic_auth_str
from requests.models import PreparedRequest, Request
from requests.sessions import Session

URL = "http://127.0.0.1:54897/basic-auth/user/pass"

# --- Build the request exactly as Session.request does (trace lines 39-44). ---
session = Session()
req = Request(
    method="get".upper(),
    url=URL,
    headers=None,
    files=None,
    data=None or {},      # sessions.py:628 -> data or {}
    json=None,
    params=None or {},    # sessions.py:633 -> params or {}
    auth=("user", "pass"),
    cookies=None,
    hooks=None,
)
# Request.__init__ normalises the empty containers (models.py:336-341).
assert req.data == {}
assert req.files == []
assert req.method == "GET"

prep = session.prepare_request(req)

# --- Chapter 5's entry state: no body was produced. ---
assert prep.body is None

# prepare_content_length wrote nothing, because method is GET (models.py:662-668).
assert "Content-Length" not in prep.headers
assert prep.headers.get("Content-Length") is None
# No content type either: files was empty and data was falsy.
assert "Content-Type" not in prep.headers

# --- The tuple became a header (trace lines 173-183). ---
assert prep.headers["Authorization"] == "Basic dXNlcjpwYXNz"
# Same value the auth helper produces directly.
assert _basic_auth_str("user", "pass") == "Basic dXNlcjpwYXNz"
# And it is reversible, not encrypted -- hence the http:// warning in the story.
import base64

assert base64.b64decode("dXNlcjpwYXNz") == b"user:pass"

# HTTPBasicAuth mutates in place and returns the same object (auth.py:111-113).
probe = PreparedRequest()
probe.prepare(method="GET", url=URL, headers={}, auth=None)
returned = HTTPBasicAuth("user", "pass")(probe)
assert returned is probe
assert probe.headers["Authorization"] == "Basic dXNlcjpwYXNz"

# --- Exact exit state of the chapter (trace line 192). ---
assert prep.method == "GET"
assert prep.url == URL
assert dict(prep.headers) == {
    "User-Agent": prep.headers["User-Agent"],  # version-dependent string
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Authorization": "Basic dXNlcjpwYXNz",
}
assert prep.headers["User-Agent"].startswith("python-requests/")
assert prep.hooks == {"response": []}

# --- Contrasts the chapter claims about branches not taken. ---

# A POST with no body DOES get Content-Length: 0 (models.py:662-668).
post = PreparedRequest()
post.prepare(method="POST", url=URL, headers={}, data={})
assert post.body is None
assert post.headers["Content-Length"] == "0"

# json= is ignored when data is truthy (models.py:588).
both = PreparedRequest()
both.prepare(method="POST", url=URL, headers={}, data={"a": "b"}, json={"c": "d"})
assert both.body == "a=b"
assert both.headers["Content-Type"] == "application/x-www-form-urlencoded"

# Credentials embedded in the URL are used when auth is None (models.py:678-680).
url_auth = PreparedRequest()
url_auth.prepare(
    method="GET", url="http://user:pass@127.0.0.1:54897/x", headers={}, auth=None
)
assert url_auth.headers["Authorization"] == "Basic dXNlcjpwYXNz"

# Non-latin-1 credentials fail during preparation (auth.py:65-69).
try:
    _basic_auth_str("user", "p\u00e4ss\u20ac")
except UnicodeEncodeError:
    pass
else:
    raise AssertionError("expected UnicodeEncodeError for non-latin-1 password")

session.close()
print("chapter 5 verified")
