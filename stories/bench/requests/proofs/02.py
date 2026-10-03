"""Replays trace lines 39-85: Session.request -> Request -> Session.prepare_request.

Run from the repository root with PYTHONPATH=src.
"""

from collections import OrderedDict

from requests.models import PreparedRequest, Request
from requests.sessions import Session, merge_hooks, merge_setting
from requests.structures import CaseInsensitiveDict

URL = "http://127.0.0.1:54897/basic-auth/user/pass"

# --- the merge rules the chapter claims (sessions.py:76-124) -----------------
# session value None -> request value wins outright (this is how auth resolves)
assert merge_setting(("user", "pass"), None) == ("user", "pass")
# request value None -> session value wins
assert merge_setting(None, {"a": "1"}) == {"a": "1"}
# non-Mapping settings bypass merging entirely
assert merge_setting(True, "/path/to/bundle.pem") is True
# request keys overwrite session keys, and a None value deletes the key
merged = merge_setting(
    {"Accept": None, "X-Test": "yes"},
    CaseInsensitiveDict({"Accept": "*/*", "Connection": "keep-alive"}),
    dict_class=CaseInsensitiveDict,
)
assert "Accept" not in merged
assert merged["X-Test"] == "yes"
assert merged["Connection"] == "keep-alive"
# an empty response hook list must not wipe out the other side
assert merge_hooks({"response": []}, {"response": []}) == {"response": []}

# --- the real path, stopped exactly where chapter 2 ends ---------------------
captured = {}
real_prepare = PreparedRequest.prepare


def spy(self, **kwargs):  # chapter 3 starts inside the real prepare()
    captured.update(kwargs)


PreparedRequest.prepare = spy
try:
    with Session() as session:
        session_cookies = session.cookies

        # exactly what Session.request builds (sessions.py:622-634)
        req = Request(
            method="get".upper(),
            url=URL,
            headers=None,
            files=None,
            data=None or {},
            json=None,
            params=None or {},
            auth=("user", "pass"),
            cookies=None,
            hooks=None,
        )
        # Request.__init__ fills the holes with empty containers
        assert req.method == "GET"
        assert req.data == {}
        assert req.files == []
        assert req.headers == {}
        assert req.params == {}
        assert req.hooks == {"response": []}
        assert req.auth == ("user", "pass")

        # the netrc branch is not taken, because auth was supplied
        assert session.trust_env is True
        assert session.auth is None
        assert not (session.trust_env and not req.auth and not session.auth)

        session.prepare_request(req)

        # preparation never mutates the session's own jar
        assert session.cookies is session_cookies
        assert list(session.cookies) == []
finally:
    PreparedRequest.prepare = real_prepare

# --- what came out of the merge ---------------------------------------------
assert captured["method"] == "GET"
assert captured["url"] == URL
assert captured["files"] == []
assert captured["data"] == {}
assert captured["json"] is None
assert captured["auth"] == ("user", "pass")
assert captured["hooks"] == {"response": []}

headers = captured["headers"]
assert isinstance(headers, CaseInsensitiveDict)
assert dict(headers) == {
    "User-Agent": "python-requests/2.34.2",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

params = captured["params"]
assert isinstance(params, OrderedDict)
assert list(params.items()) == []

cookies = captured["cookies"]
assert cookies is not session_cookies  # a third, freshly merged jar
assert list(cookies) == []

print("chapter 2 ok")
