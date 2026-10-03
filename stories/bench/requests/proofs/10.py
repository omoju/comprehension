"""Replays the scenario and asserts the values the data had in chapter 10's span.

Run from the repository root with PYTHONPATH=src.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from requests.models import CONTENT_CHUNK_SIZE

BODY = json.dumps({"authenticated": True, "user": "user"}).encode("utf-8")
received_headers = {}


class BasicAuthHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        received_headers["Authorization"] = self.headers.get("Authorization")
        received_headers["User-Agent"] = self.headers.get("User-Agent")
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

    # --- the body was read inside Session.send, because stream is False ---
    # (models.py:1046 ran before requests.get() returned)
    assert r._content_consumed is True
    assert r._content == b'{"authenticated": true, "user": "user"}'
    assert CONTENT_CHUNK_SIZE == 10240  # the chunk_size the trace shows

    # --- chapter 9 left no history and no next hop ---
    assert r.history == []
    assert r._next is None

    # --- what the caller sees ---
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json; charset=utf-8"
    assert r.headers["Content-Type"] == "application/json; charset=utf-8"  # case-insensitive
    assert r.encoding == "utf-8"
    assert r.content == b'{"authenticated": true, "user": "user"}'
    assert r.text == '{"authenticated": true, "user": "user"}'
    assert r.json() == {"authenticated": True, "user": "user"}

    # json() is recomputed, not cached: two calls, two distinct objects
    assert r.json() is not r.json()

    # nothing in the success path checked the status; raise_for_status is opt-in
    assert r.raise_for_status() is None
    assert bool(r) is True

    # the Authorization header really went out on the wire (chapter 5)
    assert received_headers["Authorization"] == "Basic dXNlcjpwYXNz"
    assert received_headers["User-Agent"].startswith("python-requests/")

    # --- Session.close() clears the adapters' pools (what __exit__ did above) ---
    s = requests.Session()
    s.get(url)
    pool_manager = s.get_adapter(url).poolmanager
    assert len(pool_manager.pools) == 1
    s.close()
    assert len(pool_manager.pools) == 0
finally:
    server.shutdown()
    server.server_close()
    thread.join()

print("chapter 10 proof: ok")
