"""Replays the scenario and asserts the values the data had in chapter 8.

Run from the repository root with PYTHONPATH=src.
"""

import weakref

from jinja2 import DictLoader, Environment, select_autoescape
from jinja2.runtime import Undefined

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

loader = DictLoader({"base.html": BASE_HTML, "members.html": MEMBERS_HTML})
env = Environment(loader=loader, autoescape=select_autoescape(["html", "htm", "xml"]))

template = env.get_template("members.html")

# The parent is not loaded by loading the child: extends is resolved at render time.
base_key = (weakref.ref(env.loader), "base.html")
assert env.cache.get(base_key) is None

# The child's generated code calls get_template at runtime, with its own name as parent,
# and then appends the parent's blocks behind its own.
child_src = env.compile(MEMBERS_HTML, "members.html", None, True)
assert "parent_template = environment.get_template('base.html', 'members.html')" in child_src
assert "context.blocks.setdefault(name, []).append(parent_block)" in child_src
assert "yield from parent_template.root_render_func(context)" in child_src

# The parent's generated code calls index 0 of each block stack, not its own functions.
base_src = env.compile(BASE_HTML, "base.html", None, True)
assert "yield from context.blocks['title'][0](context)" in base_src
assert "yield from context.blocks['content'][0](context)" in base_src

# 'users' is resolved through the context and guarded against missing;
# 'user' is a loop parameter, so it is written bare.
assert "l_0_users = resolve('users')" in child_src
assert "(undefined(name='users') if l_0_users is missing else l_0_users)" in child_src

# The escaping decision was baked in at compile time, not consulted at render time.
assert "escape(environment.getattr(l_1_user, 'url'))" in child_src
assert "escape(environment.getattr(l_1_user, 'username'))" in child_src

# join_path is the naming hook, and its default returns the name unchanged.
assert env.join_path("base.html", "members.html") == "base.html"

users = [
    {"url": "/user/1", "username": "ada"},
    {"url": "/user/2", "username": "grace"},
    {"url": "/user/3", "username": "Tom & Jerry"},
]

# Render through an explicit context so the block stacks can be inspected afterwards.
ctx = template.new_context({"users": users})
assert ctx.resolve_or_missing("users") is users
assert set(ctx.blocks) == {"title", "content"}
assert len(ctx.blocks["title"]) == 1
assert len(ctx.blocks["content"]) == 1

rendered = env.concat(template.root_render_func(ctx))

# After the extends ran, each block name is a two-deep stack: child first, parent behind.
base_template = env.get_template("base.html")
assert len(ctx.blocks["title"]) == 2
assert ctx.blocks["title"][0] is template.blocks["title"]
assert ctx.blocks["title"][1] is base_template.blocks["title"]
assert len(ctx.blocks["content"]) == 2
assert ctx.blocks["content"][0] is template.blocks["content"]
assert ctx.blocks["content"][1] is base_template.blocks["content"]

# The parent is now in the same LRU cache, keyed by (weakref(loader), name).
assert env.cache.get(base_key) is base_template

# The six dynamic lookups of this render: attribute first, then item access.
assert env.getattr(users[0], "url") == "/user/1"
assert env.getattr(users[2], "username") == "Tom & Jerry"
# A name that is neither attribute nor key yields an Undefined that prints as "".
missing_attr = env.getattr(users[0], "nope")
assert isinstance(missing_attr, Undefined)
assert str(missing_attr) == ""

EXPECTED = (
    "<!DOCTYPE html>\n"
    '<html lang="en">\n'
    "<head>\n"
    "    <title>Members - My Webpage</title>\n"
    "</head>\n"
    "<body>\n"
    '    <div id="content">\n'
    "  <ul>\n"
    "  \n"
    '    <li><a href="/user/1">ada</a></li>\n'
    "  \n"
    '    <li><a href="/user/2">grace</a></li>\n'
    "  \n"
    '    <li><a href="/user/3">Tom &amp; Jerry</a></li>\n'
    "  \n"
    "  </ul>\n"
    "</div>\n"
    "</body>\n"
    "</html>"
)

assert rendered == EXPECTED
# The ampersand was escaped; the child's top-level newlines never reached the output.
assert "Tom &amp; Jerry" in rendered
assert "Tom & Jerry" not in rendered
assert rendered.startswith("<!DOCTYPE html>")

# render() takes the same road and produces the same string.
assert template.render(users=users) == EXPECTED

print("chapter 8 verified")
