import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from markupsafe import EscapeFormatter
from markupsafe import Markup
from markupsafe import escape

calls = []


class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __html_format__(self, format_spec):
        calls.append(("__html_format__", format_spec))
        if format_spec == "link":
            return Markup('<a href="/user/{}">{}</a>').format(self.id, self.__html__())
        elif format_spec:
            raise ValueError("Invalid format spec")
        return self.__html__()

    def __html__(self):
        calls.append(("__html__", None))
        return Markup('<span class="user">{0}</span>').format(self.name)


# --- trace 18-20: escape(user) takes the __html__ branch, then repr. ---
user = User(3, 'Alice "The <b>Great</b>"')
user_markup = escape(user)
assert calls == [("__html__", None)]  # escape called __html__ exactly once
assert type(user_markup) is Markup
assert str(user_markup) == (
    '<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span>'
)
# The tags from __html__ survive; only the name was escaped.
assert "<span" in user_markup and "&lt;span" not in user_markup
assert repr(user_markup) == (
    'Markup(\'<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;'
    "</span>')"
)

# --- trace 21-22: the template literal becomes Markup, unchanged. ---
template = Markup("<p>User: {user:link} said: {comment}</p>")
assert type(template) is Markup
assert str(template) == "<p>User: {user:link} said: {comment}</p>"

# --- trace 24-25: EscapeFormatter stores the bound classmethod. ---
formatter = EscapeFormatter(Markup.escape)
assert formatter.escape == Markup.escape

# --- trace 26-29: format_field dispatches to __html_format__ with 'link',
# and __html_format__ builds the anchor template. Stop at the boundary. ---
safe_comment = escape("<script>alert(document.cookie);</script>")


class Stop(Exception):
    pass


class StopUser(User):
    def __html_format__(self, format_spec):
        tpl = Markup('<a href="/user/{}">{}</a>')
        raise Stop((format_spec, type(tpl), str(tpl)))


seen = None

try:
    template.format(user=StopUser(3, "x"), comment=safe_comment)
except Stop as e:
    seen = e.args[0]

assert seen is not None, "format_field did not reach __html_format__"
assert seen == ("link", Markup, '<a href="/user/{}">{}</a>')

# --- roads not taken ---
# __html__ without __html_format__, plus a non-empty spec, raises ValueError.
class HtmlOnly:
    def __html__(self):
        return "<b>x</b>"


msg = None

try:
    Markup("{0:spec}").format(HtmlOnly())
except ValueError as e:
    msg = str(e)

assert msg is not None and msg.startswith("Format specifier spec given, but ")

# Markup itself rejects any non-empty spec.
msg2 = None

try:
    Markup("{0:>10}").format(Markup("x"))
except ValueError as e:
    msg2 = str(e)

assert msg2 == "Unsupported format specification for Markup."

# An exception from __html__ leaves escape() unchanged.
class Boom:
    def __html__(self):
        raise ValueError(123)


args = None

try:
    escape(Boom())
except ValueError as e:
    args = e.args

assert args == (123,)
print("chapter 2 proof ok")
