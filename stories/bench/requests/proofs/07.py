"""Replays the scenario through HTTPAdapter.send (trace lines 217-254)."""

import json
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from urllib3.response import HTTPResponse
from urllib3.util import Timeout as TimeoutSauce

import requests
from requests.utils import select_proxy

BODY = json.dumps({"authenticated": True, "user": "user"}).encode("utf-8")
received = {}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        received["Authorization"] = self.headers.get("Authorization")
        received["Content-Length"] = self.headers.get("Content-Length")
        received["Transfer-Encoding"] = self.headers.get("Transfer-Encoding")
        received["path"] = self.path
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)

    def log_message(self, fmt, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
host, port = server.server_address[0], server.server_address[1]
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

try:
    url = f"http://{host}:{port}/basic-auth/user/pass"
    with requests.Session() as s:
        req = requests.Request(
            method="GET", url=url, data={}, params={}, auth=("user", "pass")
        )
        prep = s.prepare_request(req)

        # Chapter 6 left us here: the adapter mounted at 'http://', no retries.
        adapter = s.get_adapter(url=prep.url)
        assert adapter is s.adapters["http://"]
        assert adapter.max_retries.total == 0
        assert adapter.max_retries.read is False

        proxies = OrderedDict()

        # get_connection_with_tls_context: no proxy, then the pool key.
        assert select_proxy(prep.url, proxies) is None
        host_params, pool_kwargs = adapter.build_connection_pool_key_attributes(
            prep, True, None
        )
        assert host_params == {"scheme": "http", "host": "127.0.0.1", "port": port}
        assert pool_kwargs == {"cert_reqs": "CERT_REQUIRED"}

        conn = adapter.get_connection_with_tls_context(
            prep, True, proxies=proxies, cert=None
        )

        # cert_verify: http URL -> the else branch, verify=True set aside.
        adapter.cert_verify(conn, prep.url, True, None)
        assert conn.cert_reqs == "CERT_NONE"
        assert conn.ca_certs is None
        assert conn.ca_cert_dir is None

        # request_url / path_url, and add_headers doing nothing.
        assert adapter.request_url(prep, proxies) == "/basic-auth/user/pass"
        assert prep.path_url == "/basic-auth/user/pass"
        assert (
            adapter.add_headers(
                prep, stream=False, timeout=None, verify=True, cert=None, proxies=proxies
            )
            is None
        )

        # A None body is not chunked.
        assert prep.body is None
        chunked = not (prep.body is None or "Content-Length" in prep.headers)
        assert chunked is False

        # timeout=None -> a Timeout with no deadlines.
        resolved_timeout = TimeoutSauce(connect=None, read=None)
        assert resolved_timeout.connect_timeout is None
        assert resolved_timeout.read_timeout is None

        # The headers urllib3 copies still carry the Basic credentials.
        copied = prep.headers.copy()
        assert copied["Authorization"] == "Basic dXNlcjpwYXNz"
        assert sorted(copied.keys()) == [
            "Accept",
            "Accept-Encoding",
            "Authorization",
            "Connection",
            "User-Agent",
        ]

        resp = adapter.send(
            prep, stream=False, timeout=None, verify=True, cert=None, proxies=proxies
        )

        # What came back from conn.urlopen: a live urllib3 response.
        assert isinstance(resp.raw, HTTPResponse)
        assert resp.raw.status == 200

        # What went out on the wire.
        assert received["path"] == "/basic-auth/user/pass"
        assert received["Authorization"] == "Basic dXNlcjpwYXNz"
        assert received["Content-Length"] is None
        assert received["Transfer-Encoding"] is None

        resp.content  # drain so the connection is released
finally:
    server.shutdown()
    server.server_close()
    thread.join()

print("chapter 7 verified")
