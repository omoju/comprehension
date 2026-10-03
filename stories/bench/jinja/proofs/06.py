"""Replay the scenario up to the end of chapter 6: members.html compiled,
exec'd into a Template object, and cached. base.html is not loaded yet.

Run from the repository root with PYTHONPATH=src (or rely on the sys.path
insert below).
"""

import sys
import weakref

sys.path.insert(0, "src")

from jinja2 import DictLoader, Environment, select_autoescape

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

# --- what the code generator wrote for the two blocks -----------------------

src = env.compile(MEMBERS_HTML, "members.html", None, True)
lines = src.splitlines()

# Both blocks became module-level functions with the same signature.
assert "def block_title(context, missing=missing, environment=environment):" in src
assert "def block_content(context, missing=missing, environment=environment):" in src

# Each block frame emits its own _block_vars dict.
assert src.count("_block_vars = {}") == 2

# title: the constant text was escaped and folded at compile time.
assert "    yield 'Members'" in lines
assert "escape('Members')" not in src

# content: the `users` load was hoisted by enter_frame as a resolve.
assert "    l_0_users = resolve('users')" in lines

# content: a plain for-loop (no LoopContext), with the undefined guard.
assert (
    "for l_1_user in (undefined(name='users') if l_0_users is missing"
    " else l_0_users):" in src
)
assert "_loop_vars = {}" in src
assert "LoopContext(" not in src

# content: the interpolations are wrapped in escape() in the *source*.
assert "yield escape(environment.getattr(l_1_user, 'url'))" in src
assert "yield escape(environment.getattr(l_1_user, 'username'))" in src

# the two closing lines
assert "blocks = {'title': block_title, 'content': block_content}" in lines
assert "debug_info = '1=12&2=17&3=27&5=37&6=41'" in lines

# debug_info really does name those generated lines (1-based -> 0-based).
assert lines[16] == "def block_title(context, missing=missing, environment=environment):"
assert lines[26] == (
    "def block_content(context, missing=missing, environment=environment):"
)

# --- compile + exec + cache -------------------------------------------------

tmpl = env.get_template("members.html")

assert tmpl.name == "members.html"
assert tmpl.filename == "<template>"          # DictLoader supplied no filename
assert sorted(tmpl.blocks) == ["content", "title"]
assert callable(tmpl.blocks["title"]) and callable(tmpl.blocks["content"])
assert tmpl.root_render_func.__name__ == "root"
assert tmpl._debug_info == "1=12&2=17&3=27&5=37&6=41"
assert tmpl.debug_info == [(1, 12), (2, 17), (3, 27), (5, 37), (6, 41)]

# exec only defined functions: nothing has been rendered.
assert tmpl._module is None

# _from_namespace planted the back-references into the generated module.
ns = tmpl.root_render_func.__globals__
assert ns["__jinja_template__"] is tmpl
assert ns["environment"] is env
assert ns["name"] == "members.html"
assert tmpl.blocks["title"] is ns["block_title"]

# from_code attached the loader's uptodate closure.
assert tmpl._uptodate is not None
assert tmpl.is_up_to_date is True

# cached under (weakref(loader), name) -- and base.html is NOT loaded yet.
key_members = (weakref.ref(env.loader), "members.html")
key_base = (weakref.ref(env.loader), "base.html")
assert env.cache.get(key_members) is tmpl
assert env.cache.get(key_base) is None
assert env.get_template("members.html") is tmpl

print("chapter 6 verified")
