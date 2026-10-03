# PYTHONPATH=src, run from the repository root.
from flask import Flask
from flask.sessions import NullSession, SecureCookieSessionInterface
from flask.testing import EnvironBuilder

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


# Chapter 1: the default that decides this chapter.
assert app.secret_key is None
assert app.config["SECRET_KEY"] is None

# Chapter 2/3: build the environ and the (unpushed) context.
builder = EnvironBuilder(
    app,
    "/",
    method="GET",
    environ_base={"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "Werkzeug/3.1.9"},
)
try:
    environ = builder.get_environ()
finally:
    builder.close()

assert environ["HTTP_HOST"] == "localhost"
assert environ["PATH_INFO"] == "/"

ctx = app.request_context(environ)
assert ctx._session is None
assert ctx._cv_token is None
assert ctx._push_count == 0
assert ctx.url_adapter is not None
assert ctx.request.url_rule is None
assert ctx.request.view_args is None

# The session interface refuses to build a serializer without a secret key,
# so open_session returns None for this request.
si = app.session_interface
assert isinstance(si, SecureCookieSessionInterface)
assert si.get_signing_serializer(app) is None
with ctx:  # open_session needs the context to be active
    assert si.open_session(app, ctx.request) is None
# the `with` block pushed and popped once; start over cleanly
ctx = app.request_context(environ)

# Chapter 4: push.
ctx.push()

assert ctx._push_count == 1
assert ctx._cv_token is not None

# The session was loaded during push, and it is a NullSession.
sess = ctx._session
assert isinstance(sess, NullSession)
assert len(sess) == 0
assert sess.get("user_id") is None
assert ("user_id" in sess) is False
# Reads are silent; writes are not.
try:
    sess["user_id"] = 1
except RuntimeError as e:
    assert "no secret key was set" in str(e)
else:
    raise AssertionError("writing to a NullSession must raise RuntimeError")

# Loading via _get_session does not mark the session accessed.
assert sess.accessed is False

# Routing ran after the session, and succeeded.
assert ctx.request.routing_exception is None
assert ctx.request.url_rule is not None
assert ctx.request.url_rule.endpoint == "hello"
assert ctx.request.view_args == {}
assert ctx.request.endpoint == "hello"
assert ctx.request.blueprints == []

# A second push is counted but does not re-run the work.
token = ctx._cv_token
ctx.push()
assert ctx._push_count == 2
assert ctx._cv_token is token
assert ctx._session is sess

print("chapter 4 holds")
