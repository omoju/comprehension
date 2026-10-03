"""Replays the scenario and asserts what Chapter 9 claims about the span
from dispatch_hook through resolve_redirects (trace lines 290-310)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from requests.hooks import dispatch_hook
from requests.models import REDIRECT_STATI
from requests.sessions import Session

BODY = json.dumps({"authenticated": True, "user": "user"}).encode("utf-8")


class BasicAuthHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)

    def log_message(self, fmt, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), BasicAuthHandler)
host, port = server.server_address[0], server.server_address[1]
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

try:
    url = f"http://{host}:{port}/basic-auth/user/pass"

    # --- Observe the Response at the moment it enters this chapter's span,
    # --- i.e. as HTTPAdapter.send returns it, before Session.send touches it.
    session = Session()
    req = requests.Request(
        method="GET", url=url, data={}, params={}, auth=("user", "pass")
    )
    prep = session.prepare_request(req)
    settings = session.merge_environment_settings(prep.url, {}, None, None, None)
    adapter = session.get_adapter(url=prep.url)
    raw_resp = adapter.send(
        prep,
        stream=settings["stream"],
        timeout=None,
        verify=settings["verify"],
        cert=settings["cert"],
        proxies=settings["proxies"],
    )

    # Enters as: a 200 whose body has not been read.
    assert raw_resp.status_code == 200
    assert raw_resp._content is False, "body must still be unread at this point"
    assert raw_resp.history == []

    # The hooks dict carried by the PreparedRequest is the empty-list form.
    assert prep.hooks == {"response": []}

    # dispatch_hook with an empty hook list returns the very same object.
    same = dispatch_hook("response", prep.hooks, raw_resp)
    assert same is raw_resp

    # A hook returning None leaves the response alone; a hook returning a
    # value replaces it. Both branches of hooks.py#L44-L47.
    assert dispatch_hook("response", {"response": lambda r, **kw: None}, raw_resp) is raw_resp
    sentinel = object()
    assert dispatch_hook("response", {"response": lambda r, **kw: sentinel}, raw_resp) is sentinel

    # The redirect question: no Location header, status not in REDIRECT_STATI.
    assert "location" not in raw_resp.headers
    assert raw_resp.status_code not in REDIRECT_STATI
    assert raw_resp.is_redirect is False
    assert session.get_redirect_target(raw_resp) is None

    # Therefore resolve_redirects yields nothing at all.
    gen = session.resolve_redirects(
        raw_resp, prep, stream=False, timeout=None, verify=True,
        cert=None, proxies=settings["proxies"],
    )
    assert list(gen) == []

    # Cookie persistence target is the Session jar; the server set none.
    assert list(session.cookies) == []
    raw_resp.content  # drain so the socket is released
    session.close()

    # --- Now the scenario proper, to confirm the end state of the span.
    r = requests.get(url, auth=("user", "pass"))
finally:
    server.shutdown()
    server.server_close()
    thread.join()

# Leaves as: untouched by hooks, no history, no next hop.
assert r.status_code == 200
assert r.history == []
assert r.next is None
assert r._next is None
assert r.headers["content-type"] == "application/json; charset=utf-8"

# The redirect-stripping rules quoted in the chapter, exercised directly.
s = Session()
assert s.should_strip_auth("http://a.example/x", "http://b.example/x") is True
assert s.should_strip_auth("http://a.example/x", "https://a.example/x") is False
assert s.should_strip_auth("https://a.example/x", "http://a.example/x") is True
assert s.should_strip_auth("http://a.example/x", "http://a.example:8080/x") is True
s.close()

# And the exact membership of REDIRECT_STATI.
assert REDIRECT_STATI == (301, 302, 303, 307, 308)
print("chapter 9 proof ok")
