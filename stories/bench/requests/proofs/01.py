"""Replays chapter 1: requests.get -> requests.api.request -> Session.__init__.

Run from the repository root with PYTHONPATH=src.
"""

from collections import OrderedDict

from requests.adapters import DEFAULT_RETRIES, HTTPAdapter
from requests.cookies import RequestsCookieJar
from requests.hooks import default_hooks
from requests.models import DEFAULT_REDIRECT_LIMIT
from requests.sessions import Session
from requests.utils import default_headers, default_user_agent

# --- the protagonist, exactly as the caller typed it -------------------------
url = "http://127.0.0.1:54897/basic-auth/user/pass"
auth = ("user", "pass")
params = None

assert params is None
assert auth == ("user", "pass")
assert isinstance(url, str) and url.startswith("http://")

# --- what default_headers() puts on every request ----------------------------
ua = default_user_agent()
assert ua.startswith("python-requests/"), ua

headers = default_headers()
assert dict(headers) == {
    "User-Agent": ua,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
}, dict(headers)
assert len(headers) == 4

# --- hooks and the empty jar -------------------------------------------------
assert default_hooks() == {"response": []}

# --- the Session the URL is about to enter -----------------------------------
with Session() as session:
    # defaults that decide the rest of the story
    assert session.verify is True
    assert session.stream is False
    assert session.trust_env is True
    assert session.auth is None
    assert session.proxies == {}
    assert session.cert is None
    assert session.max_redirects == DEFAULT_REDIRECT_LIMIT == 30

    assert session.hooks == {"response": []}
    assert isinstance(session.cookies, RequestsCookieJar)
    assert len(session.cookies) == 0

    assert dict(session.headers) == dict(headers)

    # exactly two transports, http:// and https://, nothing else
    assert isinstance(session.adapters, OrderedDict)
    assert sorted(session.adapters) == ["http://", "https://"]
    for adapter in session.adapters.values():
        assert isinstance(adapter, HTTPAdapter)
        assert adapter._pool_connections == 10
        assert adapter._pool_maxsize == 10
        assert adapter._pool_block is False
        # max_retries=0 -> Retry(0, read=False): nothing is ever retried
        assert adapter.max_retries.total == DEFAULT_RETRIES == 0
        assert adapter.max_retries.read is False

    # __enter__ hands back the session itself
    assert session.__enter__() is session

print("chapter 1 verified")
