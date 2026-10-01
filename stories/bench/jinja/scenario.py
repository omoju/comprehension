"""Render the README's "In A Nutshell" member list template.

Follows the documented flow from docs/api.rst: create an Environment with a
loader and autoescaping, load a template by name, and render it with data.
"""

import os
import sys

# The package lives in src/ in the repository.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from jinja2 import DictLoader
from jinja2 import Environment
from jinja2 import select_autoescape

BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <title>{% block title %}{% endblock %} - My Webpage</title>
</head>
<body>
    <div id="content">{% block content %}{% endblock %}</div>
</body>
</html>
"""

MEMBERS_HTML = """\
{% extends "base.html" %}
{% block title %}Members{% endblock %}
{% block content %}
  <ul>
  {% for user in users %}
    <li><a href="{{ user.url }}">{{ user.username }}</a></li>
  {% endfor %}
  </ul>
{% endblock %}
"""


def main() -> str:
    env = Environment(
        loader=DictLoader({"base.html": BASE_HTML, "members.html": MEMBERS_HTML}),
        autoescape=select_autoescape(["html", "htm", "xml"]),
    )
    template = env.get_template("members.html")

    users = [
        {"url": "/user/1", "username": "ada"},
        {"url": "/user/2", "username": "grace"},
        {"url": "/user/3", "username": "Tom & Jerry"},
    ]

    rendered = template.render(users=users)
    print(rendered)
    return rendered


if __name__ == "__main__":
    output = main()

    assert "<title>Members - My Webpage</title>" in output
    assert '<li><a href="/user/1">ada</a></li>' in output
    assert '<li><a href="/user/2">grace</a></li>' in output
    # autoescaping turned the ampersand into an HTML entity
    assert '<li><a href="/user/3">Tom &amp; Jerry</a></li>' in output
