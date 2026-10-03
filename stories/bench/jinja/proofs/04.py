"""Chapter 4: the token stream of members.html becomes a node tree."""
import sys, os

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from jinja2 import DictLoader, Environment, select_autoescape, nodes
from jinja2.exceptions import TemplateSyntaxError

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

# Exactly what the trace does inside Environment.compile.
tree = env._parse(MEMBERS_HTML, "members.html", None)

assert type(tree) is nodes.Template
body = tree.body
assert [type(n).__name__ for n in body] == [
    "Extends",
    "Output",
    "Block",
    "Output",
    "Block",
], [type(n).__name__ for n in body]

# {% extends "base.html" %} -> a constant string, nothing resolved yet.
extends = body[0]
assert extends.lineno == 1
assert isinstance(extends.template, nodes.Const)
assert extends.template.value == "base.html"

# The stray newlines survived as top-level Output nodes.
assert [n.data for n in body[1].nodes] == ["\n"]
assert [n.data for n in body[3].nodes] == ["\n"]
assert isinstance(body[1].nodes[0], nodes.TemplateData)

# {% block title %}Members{% endblock %}
title = body[2]
assert (title.name, title.scoped, title.required, title.lineno) == (
    "title",
    False,
    False,
    2,
)
assert [type(n).__name__ for n in title.body] == ["Output"]
assert title.body[0].nodes[0].data == "Members"

# {% block content %} ... {% endblock %}
content = body[4]
assert (content.name, content.scoped, content.required, content.lineno) == (
    "content",
    False,
    False,
    3,
)
assert [type(n).__name__ for n in content.body] == ["Output", "For", "Output"]
assert content.body[0].nodes[0].data == "\n  <ul>\n  "
assert content.body[2].nodes[0].data == "\n  </ul>\n"

loop = content.body[1]
assert loop.lineno == 5
assert (loop.target.name, loop.target.ctx) == ("user", "store")
assert (loop.iter.name, loop.iter.ctx) == ("users", "load")
assert loop.else_ == [] and loop.test is None and loop.recursive is False

# One Output holds the whole <li> line: text, expression, text, expression, text.
inner = loop.body[0]
assert type(inner).__name__ == "Output"
assert [type(n).__name__ for n in inner.nodes] == [
    "TemplateData",
    "Getattr",
    "TemplateData",
    "Getattr",
    "TemplateData",
]
assert inner.nodes[1].attr == "url" and inner.nodes[1].node.name == "user"
assert inner.nodes[3].attr == "username" and inner.nodes[3].node.name == "user"

# set_environment reached every node in the tree.
all_nodes = [tree, *tree.find_all(nodes.Node)]
assert len(all_nodes) > 20
assert all(n.environment is env for n in all_nodes)

# An unknown tag is a compile-time TemplateSyntaxError, not a render-time surprise.
try:
    env._parse("{% frobnicate %}", "bad.html", None)
except TemplateSyntaxError as e:
    assert "Encountered unknown tag 'frobnicate'." in str(e), str(e)
    assert e.lineno == 1
else:
    raise AssertionError("unknown tag did not fail")

print("chapter 4 ok")
