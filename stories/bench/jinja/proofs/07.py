"""Replays the scenario up to the end of chapter 7: the Context handed to root_render_func.

Run from the repository root with PYTHONPATH=src.
"""

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

# render() takes the sync path because the environment is not async
# (environment.py L1282-L1285), then builds the context (L1287).
assert env.is_async is False
ctx = template.new_context(dict(users=users))

# --- what Context.__init__ built (runtime.py L173-L184) ---
assert type(ctx) is env.context_class
assert ctx.environment is env
assert ctx.name == "members.html"
assert ctx.vars == {}
assert ctx.exported_vars == set()

# parent is a fresh plain dict: globals copied, caller vars overlaid
# (runtime.py L108). The list itself is not copied.
assert type(ctx.parent) is dict
assert ctx.parent["users"] is users
assert ctx.parent["range"] is range
assert "users" not in env.globals  # caller data did not leak into the environment

# globals_keys remembers only the globals, not the render-time vars
# (runtime.py L179).
assert "range" in ctx.globals_keys
assert "users" not in ctx.globals_keys

# each block name maps to a one-element stack, child implementation at index 0
# (runtime.py L184) -- this is what inheritance will push onto.
assert set(ctx.blocks) == {"title", "content"}
assert ctx.blocks["title"] == [template.blocks["title"]]
assert ctx.blocks["content"] == [template.blocks["content"]]
assert ctx.blocks["title"][0].__name__ == "block_title"

# the autoescape callable was consulted again, at render time, with the
# template name (nodes.py L80-L83).
assert ctx.eval_ctx.autoescape is True
assert ctx.eval_ctx.volatile is False

# nothing has rendered yet
assert template._module is None

print("chapter 7 holds")
