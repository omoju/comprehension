import weakref
from collections import ChainMap

from jinja2 import DictLoader, Environment, select_autoescape
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import LRUCache

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
env = Environment(
    loader=loader,
    autoescape=select_autoescape(["html", "htm", "xml"]),
)

# The cache key is (weakref to the loader, name) -- and it is a cold miss.
key = (weakref.ref(loader), "members.html")
assert isinstance(env.cache, LRUCache)
assert env.cache.get(key) is None

# make_globals(None) -> ChainMap({}, env.globals); writes cannot reach the env.
gs = env.make_globals(None)
assert isinstance(gs, ChainMap)
assert gs.maps[0] == {}
assert gs.maps[1] is env.globals
gs["injected"] = 1
assert "injected" not in env.globals

# DictLoader.get_source: (source, None, uptodate)
src, filename, uptodate = loader.get_source(env, "members.html")
assert src == MEMBERS_HTML
assert filename is None
assert uptodate() is True
# The mapping is live, not a snapshot: editing it makes the template stale.
loader.mapping["members.html"] = MEMBERS_HTML + "\n"
assert uptodate() is False
loader.mapping["members.html"] = MEMBERS_HTML
assert uptodate() is True

# An unknown name ends the journey here.
try:
    loader.get_source(env, "nope.html")
except TemplateNotFound as exc:
    assert str(exc) == "nope.html"
else:
    raise AssertionError("expected TemplateNotFound")

# Capture exactly what BaseLoader.load hands to Environment.compile.
recorded = {}
original_compile = Environment.compile


def spy(self, source, name=None, filename=None, raw=False, defer_init=False):
    recorded["handover"] = (source, name, filename)
    return original_compile(self, source, name, filename, raw, defer_init)


Environment.compile = spy
try:
    template = env.get_template("members.html")
finally:
    Environment.compile = original_compile

assert recorded["handover"] == (MEMBERS_HTML, "members.html", None)
# filename=None became "<template>" for Python's compile().
assert template.name == "members.html"
assert template.filename == "<template>"
print("chapter 2 ok")
