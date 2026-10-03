"""Chapter 8: build_response dresses a urllib3 response as a requests.Response.

Run from the repository root with PYTHONPATH=src.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from requests.adapters import HTTPAdapter
from requests.cookies import RequestsCookieJar
from requests.structures import CaseInsensitiveDict
from requests.utils import _parse_content_type_header, get_encoding_from_headers

BODY = json.dumps({"authenticated": True, "user": "user"}).encode("utf-8")
assert len(BODY) == 39  # the Content-Length the trace shows


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
    r = requests.get(url, auth=("user", "pass"))
finally:
    server.shutdown()
    server.server_close()
    thread.join()

# --- what build_response put on the Response (adapters.py L376-L399) ---
assert r.status_code == 200                      # getattr(resp, "status", None)
assert repr(r) == "<Response [200]>"
assert isinstance(r.headers, CaseInsensitiveDict)
assert r.headers["Content-Type"] == "application/json; charset=utf-8"
assert r.headers["content-type"] == "application/json; charset=utf-8"  # case-folded
assert r.headers["Content-Length"] == "39"
assert r.encoding == "utf-8"                     # get_encoding_from_headers
assert r.reason == "OK"                          # from response.raw.reason
assert r.url == url                              # copied from req.url
assert isinstance(r.cookies, RequestsCookieJar)
assert list(r.cookies) == []                     # server sent no Set-Cookie
assert r.history == []
assert isinstance(r.connection, HTTPAdapter)     # response.connection = self
assert r.request.headers["Authorization"] == "Basic dXNlcjpwYXNz"

# --- the encoding decision is made from headers alone (utils.py L547-L591) ---
assert _parse_content_type_header("application/json; charset=utf-8") == (
    "application/json",
    {"charset": "utf-8"},
)
assert (
    get_encoding_from_headers(
        CaseInsensitiveDict({"Content-Type": "application/json; charset=utf-8"})
    )
    == "utf-8"
)
assert (
    get_encoding_from_headers(CaseInsensitiveDict({"Content-Type": "text/html"}))
    == "ISO-8859-1"
)
assert (
    get_encoding_from_headers(CaseInsensitiveDict({"Content-Type": "application/json"}))
    == "utf-8"
)
assert get_encoding_from_headers(CaseInsensitiveDict({})) is None

# --- the two silent fallbacks: missing status, and missing _original_response ---
class FakeRaw:
    headers = {"Content-Type": "application/json"}  # no `status` attribute
    reason = "OK"
    # no `_original_response`, so extract_cookies_to_jar returns early


adapter = HTTPAdapter()
dressed = adapter.build_response(r.request, FakeRaw())
assert dressed.status_code is None               # getattr fallback, no exception
assert dressed.reason == "OK"
assert dressed.encoding == "utf-8"
assert list(dressed.cookies) == []               # cookie extraction was a no-op
assert dressed.connection is adapter
assert dressed.request is r.request
assert dressed.url == url
adapter.close()

print("chapter 8 ok")
