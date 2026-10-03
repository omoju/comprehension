"""Replay the scenario through the end of Chapter 2: the test client is
created and turns ("/", method="GET") into a WSGI environ."""

import importlib.metadata

from flask import Flask
from flask.testing import FlaskClient

app = Flask("__main__")


@app.route("/")
def hello():
    return "Hello, World!"


# --- trace 61-66: Flask.test_client -> FlaskClient.__init__ ---------------
client = app.test_client()
assert type(client) is FlaskClient  # test_client_class was None
assert client.application is app
assert client.preserve_context is False

wz = importlib.metadata.version("werkzeug")
assert client.environ_base == {
    "REMOTE_ADDR": "127.0.0.1",
    "HTTP_USER_AGENT": f"Werkzeug/{wz}",
}

# --- trace 69-70: FlaskClient._copy_environ(other={}) ---------------------
base = client._copy_environ({})
assert base == {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": f"Werkzeug/{wz}"}
# preserve_context is False outside a `with client:` block, so no hook is added
assert "werkzeug.debug.preserve_context" not in base

# the app config values EnvironBuilder reads to invent the base URL
assert app.config.get("SERVER_NAME") is None
assert app.config["APPLICATION_ROOT"] == "/"
assert app.config["PREFERRED_URL_SCHEME"] == "http"

# --- trace 68-73: _request_from_builder_args -> EnvironBuilder -> Request -
request = client._request_from_builder_args(("/",), {"method": "GET"})
environ = request.environ

assert request.method == "GET"
assert request.url == "http://localhost/"
assert request.host == "localhost"
assert environ["HTTP_HOST"] == "localhost"
assert environ["PATH_INFO"] == "/"
assert environ["QUERY_STRING"] == ""
assert environ["RAW_URI"] == "/"
assert environ["REMOTE_ADDR"] == "127.0.0.1"
assert environ["HTTP_USER_AGENT"] == f"Werkzeug/{wz}"
assert environ["wsgi.url_scheme"] == "http"

print("chapter 2 verified")
