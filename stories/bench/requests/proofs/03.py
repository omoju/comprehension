"""Replays Chapter 3: PreparedRequest.prepare_method + prepare_url.

Run from the repository root with PYTHONPATH=src.
"""

from collections import OrderedDict

from requests._internal_utils import unicode_is_ascii
from requests.exceptions import InvalidURL, MissingSchema
from requests.models import PreparedRequest
from requests.utils import requote_uri

URL = "http://127.0.0.1:54897/basic-auth/user/pass"

# The object as prepare() receives it: everything empty.
p = PreparedRequest()
assert p.method is None
assert p.url is None
assert p.headers is None
assert p.body is None
assert p._cookies is None
assert p.hooks == {"response": []}

# --- prepare_method (trace lines 87-90) -------------------------------
p.prepare_method("get")  # lowercase in, normalised out
assert p.method == "GET"

# --- prepare_url (trace lines 91-104) ---------------------------------
assert unicode_is_ascii("127.0.0.1") is True
# _encode_params(OrderedDict()) -> '' (trace line 94-99)
assert PreparedRequest._encode_params(OrderedDict()) == ""
# requote_uri is a no-op on this already-clean URL (trace line 100-103)
assert requote_uri(URL) == URL

p.prepare_url(URL, OrderedDict())
assert p.url == URL

# State at the end of the span: only method and url are set.
assert p.headers is None
assert p.body is None
assert p._cookies is None

# --- roads not taken --------------------------------------------------

# Leading whitespace is stripped silently.
w = PreparedRequest()
w.prepare_url("   " + URL, OrderedDict())
assert w.url == URL

# A colon-bearing, non-http URL is stored verbatim with no validation.
m = PreparedRequest()
m.prepare_url("mailto:user@example.com", None)
assert m.url == "mailto:user@example.com"

# No scheme -> MissingSchema, before any socket.
n = PreparedRequest()
try:
    n.prepare_url("127.0.0.1:54897/basic-auth/user/pass".replace("127.0.0.1:54897", "example.com"), None)
except MissingSchema as e:
    assert "No scheme supplied" in str(e)
else:
    raise AssertionError("expected MissingSchema")

# Wildcard host -> InvalidURL.
s = PreparedRequest()
try:
    s.prepare_url("http://*.example.com/", None)
except InvalidURL as e:
    assert "invalid label" in str(e)
else:
    raise AssertionError("expected InvalidURL")

# Params are appended to an existing query string with '&', params last.
q = PreparedRequest()
q.prepare_url("http://127.0.0.1:54897/p?a=1", {"b": "2"})
assert q.url == "http://127.0.0.1:54897/p?a=1&b=2"

# A param whose value is None is dropped entirely.
d = PreparedRequest()
d.prepare_url("http://127.0.0.1:54897/p", {"a": "1", "b": None})
assert d.url == "http://127.0.0.1:54897/p?a=1"

print("chapter 3 proof ok:", p.method, p.url)
