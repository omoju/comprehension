"""The README's first example, served from a local loopback HTTP server.

A single GET with HTTP Basic Auth travels from requests.get() through the
Session, PreparedRequest and HTTPAdapter, and comes back as a Response whose
JSON body we decode.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

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
        pass  # keep the story quiet


server = ThreadingHTTPServer(("127.0.0.1", 0), BasicAuthHandler)
host, port = server.server_address[0], server.server_address[1]
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

try:
    url = f"http://{host}:{port}/basic-auth/user/pass"
    r = requests.get(url, auth=("user", "pass"))

    print(r.status_code)
    print(r.headers["content-type"])
    print(r.encoding)
    print(r.text)
    print(r.json())
finally:
    server.shutdown()
    server.server_close()
    thread.join()

# The credentials were turned into a Basic auth header on the way out...
assert received_headers["Authorization"] == "Basic dXNlcjpwYXNz"
assert received_headers["User-Agent"].startswith("python-requests/")

# ...and the response came back decoded exactly as the README promises.
assert r.status_code == 200
assert r.headers["content-type"] == "application/json; charset=utf-8"
assert r.encoding == "utf-8"
assert r.json() == {"authenticated": True, "user": "user"}
