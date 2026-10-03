"""Chapter 6: dispatch_request -> ensure_sync -> view -> make_response."""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


# The rule registered in Chapter 1, with the flag dispatch_request reads.
rule = next(r for r in app.url_map.iter_rules() if r.rule == "/")
assert rule.endpoint == "hello"
assert rule.provide_automatic_options is True
assert "GET" in rule.methods
assert "OPTIONS" in rule.methods  # added automatically at registration

ctx = app.test_request_context("/")
ctx.push()
try:
    # Branch one is not taken: nothing was parked on the request.
    assert ctx.request.routing_exception is None
    assert ctx.request.url_rule is rule
    assert ctx.request.view_args == {}
    # Branch two is not taken: the flag is set but the method is GET.
    assert ctx.request.method == "GET"

    # ensure_sync returns a plain def unchanged.
    assert app.ensure_sync(hello) is hello

    # Branch three: the view is called, returning a bare str.
    rv = app.dispatch_request(ctx)
    assert rv == "Hello, World!"
    assert isinstance(rv, str)

    # make_response turns the str into the Response the trace recorded.
    response = app.make_response(rv)
    assert isinstance(response, app.response_class)
    assert response.status == "200 OK"
    assert response.status_code == 200
    assert response.get_data() == b"Hello, World!"
    assert len(response.get_data()) == 13  # "13 bytes" in the trace repr
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"

    # A view that returns None is refused, not silently emptied.
    try:
        app.make_response(None)
    except TypeError as e:
        assert "did not" in str(e) and "valid response" in str(e)
        assert "hello" in str(e)  # the endpoint is named in the message
    else:
        raise AssertionError("make_response(None) should raise TypeError")

    # Tuples of the wrong length are refused too.
    try:
        app.make_response(("body", 200, {}, {}))
    except TypeError as e:
        assert "valid response tuple" in str(e)
    else:
        raise AssertionError("4-tuple should raise TypeError")
finally:
    ctx.pop()

# And the same response reaches the client through the full WSGI path.
client = app.test_client()
full = client.get("/")
assert full.status == "200 OK"
assert full.headers["Content-Type"] == "text/html; charset=utf-8"
assert full.get_data(as_text=True) == "Hello, World!"

print("chapter 6 verified")
