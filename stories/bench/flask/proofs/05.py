"""Replay the scenario up to the end of Chapter 5's span.

Run from the repository root with PYTHONPATH=src.
"""

from flask import Flask
from flask.testing import EnvironBuilder

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


# Chapter 2: the test client builds the environ.
builder = EnvironBuilder(app, "/", method="GET")
try:
    environ = builder.get_environ()
finally:
    builder.close()

# Chapters 3 and 4: the context is created, bound, and pushed.
ctx = app.request_context(environ)
ctx.push()
assert ctx.request.url_rule is not None
assert ctx.request.url_rule.endpoint == "hello"
assert ctx.request.routing_exception is None

# --- Chapter 5 begins here. ---

# The deprecated hook is not overridden, so no DeprecationWarning branch runs.
assert app.should_ignore_error is None

# Setup is still open at the moment full_dispatch_request is entered.
assert app._got_first_request is False
app.route("/still-open")(lambda: "")  # accepted

# This is the assignment at src/flask/app.py:1013.
app._got_first_request = True

# The setup lock is now engaged for every setupmethod.
try:
    app.route("/too-late")
except AssertionError as e:
    assert "can no longer be called" in str(e), str(e)
else:
    raise AssertionError("expected the setup lock to refuse the late route")

# The scopes preprocess_request will consider: app only.
assert ctx.request.endpoint == "hello"
assert ctx.request.blueprint is None
assert ctx.request.blueprints == []
assert None not in app.url_value_preprocessors
assert None not in app.before_request_funcs

# No hook short-circuits the request.
rv = app.preprocess_request(ctx)
assert rv is None

print("chapter 5 verified")
