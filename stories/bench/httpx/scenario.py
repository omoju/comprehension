"""Send a request with httpx directly into a WSGI application.

Follows the documented example in docs/advanced/transports.md ("WSGI Transport"),
using a plain WSGI callable instead of Flask so no extra dependencies are needed.
"""

import httpx


def app(environ, start_response):
    # A minimal WSGI "Hello World!" application, equivalent to the Flask app
    # shown in the HTTPX documentation.
    assert environ["REQUEST_METHOD"] == "GET"
    assert environ["PATH_INFO"] == "/"

    body = b"Hello World!"
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


transport = httpx.WSGITransport(app=app)

with httpx.Client(transport=transport, base_url="http://testserver") as client:
    response = client.get("/", headers={"X-Custom": "value"})

    print(response)                       # <Response [200 OK]>
    print(response.request.url)           # http://testserver/
    print(response.headers["content-type"])
    print(response.text)

    assert response.request.headers["X-Custom"] == "value"
    assert response.status_code == 200
    assert response.text == "Hello World!"
