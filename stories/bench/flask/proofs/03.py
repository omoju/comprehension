"""Chapter 3: environ -> AppContext, via Flask.__call__ / wsgi_app / request_context.

Run from the repository root with PYTHONPATH=src.
"""

import flask
from flask import Flask
from flask.ctx import AppContext
from flask.testing import EnvironBuilder
from werkzeug.routing import MapAdapter

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


def build_environ(**kwargs):
    builder = EnvironBuilder(
        app,
        "/",
        environ_base={
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "Werkzeug/3.1.9",
        },
        **kwargs,
    )
    try:
        return builder.get_environ()
    finally:
        builder.close()


# --- the data entering this chapter (end of chapter 2) ---------------------
environ = build_environ()
assert environ["PATH_INFO"] == "/"
assert environ["HTTP_HOST"] == "localhost"
assert environ["REQUEST_METHOD"] == "GET"
assert environ["REMOTE_ADDR"] == "127.0.0.1"

# --- Flask.__call__ delegates to the *instance* attribute wsgi_app ---------
mw_app = Flask(__name__)
seen = []


def fake_wsgi_app(environ, start_response):
    seen.append(environ["PATH_INFO"])
    return [b""]


mw_app.wsgi_app = fake_wsgi_app
result = mw_app(environ, lambda status, headers: None)
assert seen == ["/"], seen
assert result == [b""]

# --- request_context -> AppContext.from_environ -> AppContext.__init__ -----
ctx = app.request_context(environ)
assert type(ctx) is AppContext
assert ctx.app is app
assert ctx.has_request is True
assert ctx.request.environ is environ
assert ctx.request.json_module is app.json
assert ctx.request.method == "GET"
assert ctx.request.host == "localhost"

# nothing has been matched or loaded yet
assert ctx.request.routing_exception is None
assert ctx.request.url_rule is None
assert ctx.request.view_args is None
assert ctx._session is None
assert ctx._flashes is None
assert ctx._after_request_functions == []

# built, but not pushed: invisible to the proxies
assert ctx._cv_token is None
assert ctx._push_count == 0
assert flask.globals._cv_app.get(None) is None

# the URL adapter bound by create_url_adapter
assert isinstance(ctx.url_adapter, MapAdapter)
assert ctx.url_adapter.server_name == "localhost"
# subdomain_matching is False -> subdomain forced to the map default ("")
assert app.subdomain_matching is False
assert ctx.url_adapter.subdomain == ""

assert repr(ctx) == f"<AppContext {id(ctx)} of {app.name}, GET 'http://localhost/'>"

# --- TRUSTED_HOSTS defaults to None: any Host header is accepted -----------
assert app.config["TRUSTED_HOSTS"] is None
evil_environ = build_environ(base_url="http://evil.example/")
evil_ctx = app.request_context(evil_environ)
assert evil_ctx.request.host == "evil.example"
assert evil_ctx.request.routing_exception is None
assert isinstance(evil_ctx.url_adapter, MapAdapter)

# --- opting in: the HTTPException is parked, not raised --------------------
app.config["TRUSTED_HOSTS"] = ["localhost"]
guarded_ctx = app.request_context(build_environ(base_url="http://evil.example/"))
assert guarded_ctx.url_adapter is None
assert guarded_ctx.request.routing_exception is not None
assert guarded_ctx.request.routing_exception.code == 400
app.config["TRUSTED_HOSTS"] = None

print("chapter 3 ok")
