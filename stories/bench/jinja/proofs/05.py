import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from jinja2 import DictLoader, Environment, select_autoescape
from jinja2.exceptions import TemplateAssertionError
from jinja2.nodes import EvalContext

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

# visit_Template's first act: EvalContext(environment, name) asks the autoescape
# callable about the *template name*. That answer is what gets compiled in.
assert EvalContext(env, "members.html").autoescape is True
assert EvalContext(env, "members.txt").autoescape is False

# Run the same pipeline the trace ran (_parse -> _generate -> generate), but keep
# the Python source instead of the code object.
source = env.compile(MEMBERS_HTML, "members.html", raw=True)

# The header: sorted runtime exports, no async names, and the load name.
assert source.startswith(
    "from jinja2.runtime import LoopContext, Macro, Markup, Namespace,"
    " TemplateNotFound, TemplateReference, TemplateRuntimeError, Undefined,"
    " escape, identity, internalcode, markup_join, missing, str_join\n"
)
assert "\nname = 'members.html'\n" in source

# Everything up to the first block function is the root function.
root_part = source.split("def block_title")[0]

# defer_init is False, so the environment is captured as a default argument.
assert "def root(context, missing=missing, environment=environment):" in root_part

# write_commons, including the dead branch that forces a generator and the
# hardcoded Undefined for inline-if else.
for line in (
    "resolve = context.resolve_or_missing",
    "undefined = environment.undefined",
    "concat = environment.concat",
    "cond_expr_undefined = Undefined",
    "if 0: yield None",
):
    assert line in root_part, line

# have_extends -> parent_template is declared, and visit_Extends emits a runtime
# get_template plus the block-copy loop that puts the parent's blocks *behind*
# the child's.
assert "parent_template = None" in root_part
assert (
    "parent_template = environment.get_template('base.html', 'members.html')"
    in root_part
)
assert "for name, parent_block in parent_template.blocks.items():" in root_part
assert "context.blocks.setdefault(name, []).append(parent_block)" in root_part

# has_known_extends is True, so no runtime guard is emitted ...
assert "if parent_template is not None:" not in source
# ... and the root function ends by delegating to the parent.
assert "yield from parent_template.root_render_func(context)" in root_part

# The two top-level Output(TemplateData('\n')) nodes were dropped by visit_Output.
assert "yield '\\n'" not in root_part

# debug_info records 1=12: template line 1 maps to generated line 12, the
# get_template call. Confirm the line count lands exactly there.
assert source.splitlines()[11].strip().startswith(
    "parent_template = environment.get_template("
), source.splitlines()[11]
assert "debug_info = '1=12&2=17&3=27&5=37&6=41'" in source

# A second root-level extends compiles to a runtime error, and CompilerExit stops
# the rest of the top-level body from being compiled.
twice = env.compile(
    '{% extends "base.html" %}{% extends "base.html" %}', "twice.html", raw=True
)
assert 'raise TemplateRuntimeError("extended multiple times")' in twice

# Duplicate block names are a compile-time failure, not last-one-wins.
try:
    env.compile(
        "{% block a %}1{% endblock %}{% block a %}2{% endblock %}",
        "dup.html",
        raw=True,
    )
except TemplateAssertionError as e:
    assert "block 'a' defined twice" in str(e), str(e)
else:
    raise AssertionError("duplicate block name did not fail compilation")

print("chapter 5 proof ok")
