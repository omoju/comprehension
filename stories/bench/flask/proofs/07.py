"""Replays the README app through one request and asserts what
process_response saw and did (trace lines 122-137).

Run from the repository root with PYTHONPATH=src.
"""

import types

from flask import Flask
from flask import request_finished
from flask.sessions import NullSession

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


# Record what process_response is handed and what it hands back.
seen = {}
base_process_response = Flask.process_response


def spy(self, ctx, response):
    seen["blueprints"] = list(ctx.request.blueprints)
    seen["ctx_after_request_functions"] = list(ctx._after_request_functions)
    seen["app_after_request_funcs"] = dict(self.after_request_funcs)
    seen["session"] = ctx._get_session()
    seen["is_null"] = self.session_interface.is_null_session(ctx._get_session())
    seen["in"] = response
    out = base_process_response(self, ctx, response)
    seen["out"] = out
    return out


app.process_response = types.MethodType(spy, app)

# finalize_request sends request_finished with the finished response.
finished = []


def record_finished(sender, response, **extra):
    finished.append(response)


request_finished.connect(record_finished, app)

client = app.test_client()
response = client.get("/")

# --- what the scope loops had to work with -------------------------------
# Endpoint 'hello' has no dot, so Request.blueprints is [].
assert seen["blueprints"] == [], seen["blueprints"]
# after_this_request was never used: the per-request list is empty.
assert seen["ctx_after_request_functions"] == []
# No @app.after_request was registered, so there is no None scope to run.
assert None not in seen["app_after_request_funcs"]

# --- the session branch that was not taken -------------------------------
assert app.secret_key is None
assert isinstance(seen["session"], NullSession)
assert dict(seen["session"]) == {}
assert seen["is_null"] is True
# NullSession refuses writes rather than silently dropping them.
try:
    seen["session"]["x"] = 1
except RuntimeError as e:
    assert "no secret key was set" in str(e), str(e)
else:
    raise AssertionError("NullSession accepted a write")

# --- process_response returned the very same object ----------------------
assert seen["out"] is seen["in"]

# --- and therefore no cookie and no Vary header were added ---------------
assert "Set-Cookie" not in response.headers
assert "Vary" not in response.headers

# --- finalize_request sent request_finished with that response -----------
assert len(finished) == 1
assert finished[0] is seen["out"]

# --- the response that leaves the span -----------------------------------
assert response.status_code == 200
assert response.headers["Content-Type"] == "text/html; charset=utf-8"
assert response.get_data() == b"Hello, World!"
assert len(response.get_data()) == 13

print("chapter 7 verified")
