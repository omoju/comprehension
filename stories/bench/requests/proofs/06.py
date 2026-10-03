"""Replays the scenario up to the end of Chapter 6: settings merge + adapter choice."""

import os
from collections import OrderedDict

from requests.adapters import HTTPAdapter
from requests.exceptions import InvalidSchema
from requests.models import Request
from requests.sessions import Session
from requests.utils import resolve_proxies

# The scenario runs with no proxy / CA-bundle configuration in the environment.
for var in (
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
):
    os.environ.pop(var, None)

url = "http://127.0.0.1:54897/basic-auth/user/pass"

with Session() as session:
    # --- Chapters 2-5: the PreparedRequest that enters this span ---------------
    req = Request(
        method="GET", url=url, headers=None, files=None, data={}, params={},
        auth=("user", "pass"), cookies=None, hooks=None, json=None,
    )
    prep = session.prepare_request(req)
    assert prep.method == "GET"
    assert prep.url == url
    assert prep.body is None
    assert prep.headers["Authorization"] == "Basic dXNlcjpwYXNz"

    # --- Session defaults that feed the merge (Chapter 1) ----------------------
    assert session.trust_env is True
    assert session.verify is True
    assert session.stream is False
    assert session.cert is None
    assert session.proxies == {}

    # --- merge_environment_settings (trace line 195-211) -----------------------
    settings = session.merge_environment_settings(prep.url, {}, None, None, None)
    assert settings == {
        "cert": None,
        "proxies": OrderedDict(),
        "stream": False,
        "verify": True,
    }
    assert isinstance(settings["proxies"], OrderedDict)
    assert settings["verify"] is True   # session default won over request None
    assert settings["stream"] is False  # session default won over request None
    assert settings["cert"] is None

    # A per-request non-dict setting bypasses merging entirely.
    assert session.merge_environment_settings(prep.url, {}, None, False, None)[
        "verify"
    ] is False

    # --- send_kwargs assembled in Session.request (lines 645-651) --------------
    send_kwargs = {"timeout": None, "allow_redirects": True}
    send_kwargs.update(settings)
    assert send_kwargs == {
        "timeout": None,
        "allow_redirects": True,
        "cert": None,
        "proxies": OrderedDict(),
        "stream": False,
        "verify": True,
    }

    # --- get_adapter (trace line 215) ------------------------------------------
    adapter = session.get_adapter(url=prep.url)
    assert adapter is session.adapters["http://"]
    assert adapter is not session.adapters["https://"]
    assert isinstance(adapter, HTTPAdapter)
    assert adapter.max_retries.total == 0  # no retries by default

    # Prefix matching is a plain startswith, and mount keeps longer keys first.
    sentinel = HTTPAdapter()
    session.mount("http://localhost", sentinel)
    assert list(session.adapters)[0] == "http://localhost"
    assert session.get_adapter("http://localhost.evil.com/x") is sentinel

    # Unmounted schemes fail here, not during URL preparation.
    try:
        session.get_adapter("mailto:nobody@example.com")
    except InvalidSchema as exc:
        assert "No connection adapters were found" in str(exc)
    else:
        raise AssertionError("expected InvalidSchema for mailto:")

    # The proxies fallback inside Session.send, exercised directly.
    assert resolve_proxies(prep, {}, trust_env=False) == {}

    # Session.send refuses an unprepared Request by name.
    try:
        session.send(req)
    except ValueError as exc:
        assert str(exc) == "You can only send PreparedRequests."
    else:
        raise AssertionError("expected ValueError for a Request")

print("chapter 6 ok")
