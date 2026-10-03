import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from collections import deque

from jinja2 import DictLoader, Environment, select_autoescape
from jinja2.exceptions import TemplateSyntaxError
from jinja2.lexer import Token, TokenStream, get_lexer
from jinja2.parser import Parser

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

# --- what chapter 2 handed over ------------------------------------------
source, filename, _uptodate = env.loader.get_source(env, "members.html")
assert source == MEMBERS_HTML
assert filename is None
assert source.startswith('{% extends "base.html" %}\n{% block t')

# --- preprocess: no extensions, so the string comes back identical --------
assert env.extensions == {}
assert env.preprocess(source, "members.html", None) == source

# --- the lexer is cached by syntax options only ---------------------------
lexer = env.lexer
assert get_lexer(env) is lexer
plain = Environment()  # different loader/autoescape, same delimiters
assert plain.lexer is lexer
other = Environment(variable_start_string="${", variable_end_string="}")
assert other.lexer is not lexer

# --- keep_trailing_newline=False drops the template's final newline -------
raw = list(lexer.tokeniter(MEMBERS_HTML, "members.html"))
assert raw[-1][1:] == ("block_end", "%}")
keep = Environment(keep_trailing_newline=True)
raw_keep = list(keep.lexer.tokeniter(MEMBERS_HTML, "members.html"))
assert raw_keep[-1][1:] == ("data", "\n")

# --- the stream this chapter produces -------------------------------------
stream = env._tokenize(source, "members.html", None, None)
assert isinstance(stream, TokenStream)
assert stream.name == "members.html"
assert stream.filename is None
assert stream.closed is False
assert stream.current == Token(1, "block_begin", "{%")
assert stream._pushed == deque()  # nothing read ahead; the rest is still lazy

# the Parser constructor produces exactly the same state
parser = Parser(env, source, "members.html", None)
assert parser.extensions == {}
assert parser._tag_stack == []
assert parser.stream.current == Token(1, "block_begin", "{%")

# --- lexer-level failures surface as TemplateSyntaxError on the template ---
try:
    env.compile("{{ foo }", "bad.html")
except TemplateSyntaxError as e:
    assert e.name == "bad.html"
    assert e.lineno == 1
    assert "unexpected '}'" in e.message
else:
    raise AssertionError("expected a TemplateSyntaxError")

print("chapter 3 verified")
