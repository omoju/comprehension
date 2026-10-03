"""Chapter 8: ctx.pop() — teardown order, error collection, and the way out.

Run from the repository root with PYTHONPATH=src.
"""

from flask import Flask
from flask.globals import _cv_app
from flask.helpers import _CollectErrors
from flask.signals import appcontext_popped
from flask.signals import appcontext_tearing_down
from flask.signals import request_tearing_down
from flask.testing import EnvironBuilder
from flask.wrappers import Request

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


events = []


def on_request_tearing_down(sender, exc=None, **extra):
    events.append(("request_tearing_down", exc, _cv_app.get(None) is not None))


def on_appcontext_tearing_down(sender, exc=None, **extra):
    events.append(("appcontext_tearing_down", exc, _cv_app.get(None) is not None))


def on_appcontext_popped(sender, **extra):
    events.append(("appcontext_popped", None, _cv_app.get(None) is not None))


request_tearing_down.connect(on_request_tearing_down, app)
appcontext_tearing_down.connect(on_appcontext_tearing_down, app)
appcontext_popped.connect(on_appcontext_popped, app)

client = app.test_client()
response = client.get("/")

# The response the scenario asserts on (Chapters 6-7).
assert response.status == "200 OK"
assert response.get_data() == b"Hello, World!"
assert len(response.get_data()) == 13
assert "Set-Cookie" not in response.headers
assert "Vary" not in response.headers

# Teardown order, exc=None, and the contextvar reset sitting between
# appcontext teardown and the popped signal (ctx.py:498-502).
assert events == [
    ("request_tearing_down", None, True),
    ("appcontext_tearing_down", None, True),
    ("appcontext_popped", None, False),
]

# The context was popped: nothing active after the request.
assert _cv_app.get(None) is None


# wsgi_app returns a ClosingIterator, and ctx.pop() ran in the `finally`
# before the body was ever iterated (app.py:1607-1619).
builder = EnvironBuilder(app, "/")
environ = builder.get_environ()
builder.close()

captured = []


def start_response(status, headers, exc_info=None):
    captured.append((status, headers))
    return lambda data: None


rv = app(environ, start_response)
assert type(rv).__name__ == "ClosingIterator"
assert captured[0][0] == "200 OK"
assert _cv_app.get(None) is None  # popped before iteration
assert b"".join(rv) == b"Hello, World!"


# _push_count: cleanup only on the last pop (ctx.py:481-484), and popping
# an unpushed context is a hard error (ctx.py:465-466).
ctx = app.test_request_context("/")
ctx.push()
ctx.push()
assert ctx._push_count == 2
ctx.pop()
assert ctx._push_count == 1
assert _cv_app.get(None) is ctx  # still active
ctx.pop()
assert _cv_app.get(None) is None
assert ctx._cv_token is None

try:
    ctx.pop()
except RuntimeError as e:
    assert "it is not pushed" in str(e)
else:
    raise AssertionError("expected RuntimeError from popping twice")


# _CollectErrors: every block runs, the error is recorded, raise_any surfaces it.
collect = _CollectErrors()
ran = []

for i in (0, 1, 2):
    with collect:
        ran.append(i)
        if i == 1:
            raise ValueError("boom 1")

assert ran == [0, 1, 2]
assert len(collect.errors) == 1

try:
    collect.raise_any("Errors during request teardown")
except BaseException as e:
    assert "boom 1" in repr(e)
else:
    raise AssertionError("expected raise_any to raise")


# request.close() runs between the two teardown phases, context still active
# (ctx.py:488-496).
close_events = []


class RecordingRequest(Request):
    def close(self):
        close_events.append(("request_closed", _cv_app.get(None) is not None))
        super().close()


app2 = Flask(__name__)
app2.request_class = RecordingRequest


@app2.route("/")
def hello2():
    return "Hello, World!"


@app2.teardown_request
def teardown_req(exc):
    close_events.append(("teardown_request", exc))


@app2.teardown_appcontext
def teardown_app(exc):
    close_events.append(("teardown_appcontext", exc))


app2.test_client().get("/")
assert close_events[:3] == [
    ("teardown_request", None),
    ("request_closed", True),
    ("teardown_appcontext", None),
]

print("chapter 8 proof ok")
