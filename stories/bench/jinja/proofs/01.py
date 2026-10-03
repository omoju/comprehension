"""Replays trace lines 2-17: building the world the template source enters."""

from jinja2 import DictLoader, Environment, select_autoescape
from jinja2.environment import create_cache
from jinja2.runtime import Undefined
from jinja2.utils import LRUCache

BASE_HTML = (
    "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
    "    <title>{% block title %}{% endblock %} - My Webpage</title>\n"
    "</head>\n<body>\n"
    "    <div id=\"content\">{% block content %}{% endblock %}</div>\n"
    "</body>\n</html>\n"
)
MEMBERS_HTML = (
    '{% extends "base.html" %}\n'
    "{% block title %}Members{% endblock %}\n"
    "{% block content %}\n  <ul>\n  {% for user in users %}\n"
    '    <li><a href="{{ user.url }}">{{ user.username }}</a></li>\n'
    "  {% endfor %}\n  </ul>\n{% endblock %}\n"
)

# --- trace line 2: DictLoader.__init__ -------------------------------------
mapping = {"base.html": BASE_HTML, "members.html": MEMBERS_HTML}
loader = DictLoader(mapping)
# The loader takes custody by reference; no copy, no inspection of the source.
assert loader.mapping is mapping
assert loader.mapping["members.html"] == MEMBERS_HTML

# --- trace line 4: select_autoescape ---------------------------------------
autoescape = select_autoescape(["html", "htm", "xml"])
assert callable(autoescape)
# It is a policy keyed on name; default=False means non-listed names are NOT escaped.
assert autoescape("members.html") is True
assert autoescape("notes.txt") is False

# --- trace lines 6-17: Environment.__init__ --------------------------------
env = Environment(loader=loader, autoescape=autoescape)

# The callable was stored, not invoked, and the bare default would have been False.
assert env.autoescape is autoescape
assert Environment().autoescape is False

# create_cache(400) -> LRUCache(400), empty.
assert isinstance(env.cache, LRUCache)
assert env.cache.capacity == 400
assert len(env.cache) == 0
# The two other shapes create_cache can return.
assert create_cache(0) is None
assert type(create_cache(-1)) is dict

# Defaults that decide cost and staleness.
assert env.auto_reload is True
assert env.bytecode_cache is None
assert env.is_async is False

# load_extensions(self, ()) -> {}: nothing may rewrite the source or the tokens.
assert env.extensions == {}
assert env.preprocess(MEMBERS_HTML, "members.html") == MEMBERS_HTML

# _environment_config_check passed: these are the invariants it asserts.
assert issubclass(env.undefined, Undefined)
assert env.block_start_string == "{%"
assert env.variable_start_string == "{{"
assert env.comment_start_string == "{#"
assert env.newline_sequence == "\n"

# And the source is still exactly the string that was handed in.
assert env.loader.mapping["members.html"] == MEMBERS_HTML
