"""The README's minimal Flask application, exercised with one request.

Save this as app.py and `flask run` would serve it; here the documented
test client sends the request through the same WSGI machinery.
"""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


if __name__ == "__main__":
    client = app.test_client()
    response = client.get("/")

    print(response.status)
    print(response.headers["Content-Type"])
    print(response.get_data(as_text=True))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Hello, World!"
