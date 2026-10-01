"""Replay the scenario through the end of chapter 4's span (trace lines 45-61).

Run from the repository root with PYTHONPATH=src.
"""

from markupsafe import EscapeFormatter
from markupsafe import Markup
from markupsafe import escape


class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __html_format__(self, format_spec):
        if format_spec == "link":
            return Markup('<a href="/user/{}">{}</a>').format(self.id, self.__html__())
        elif format_spec:
            raise ValueError("Invalid format spec")
        return self.__html__()

    def __html__(self):
        return Markup('<span class="user">{0}</span>').format(self.name)


# --- state entering this chapter (chapters 1-3) ---------------------------
safe_comment = escape("<script>alert(document.cookie);</script>")
assert safe_comment == Markup("&lt;script&gt;alert(document.cookie);&lt;/script&gt;")

user = User(3, 'Alice "The <b>Great</b>"')
anchor = user.__html_format__("link")
ANCHOR = (
    '<a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a>"
)
assert anchor == ANCHOR
assert type(anchor) is Markup

# --- trace 45-54: Markup.escape(anchor) -> escape -> __html__ -> same text
assert anchor.__html__() is anchor  # __init__.py:133-134
escaped_anchor = Markup.escape(anchor)
assert escaped_anchor == ANCHOR  # unchanged: tags survive, name stays escaped
assert type(escaped_anchor) is Markup

# the re-wrap branch at __init__.py:237-238: escape() always builds a plain
# Markup, so a subclass must put its own type back.
class MyMarkup(Markup):
    pass

plain_rv = escape(anchor)
assert type(plain_rv) is Markup  # not MyMarkup, whatever cls was asked

sub = MyMarkup.escape(anchor)
assert type(sub) is MyMarkup  # rv.__class__ is not cls -> cls(rv)
assert sub == ANCHOR

# and the base class does not gain a subclass type by accident
assert type(Markup.escape(sub)) is Markup

# --- trace 55: format_field hands vformat a *plain* str -------------------
formatter = EscapeFormatter(Markup.escape)
rv_user = formatter.format_field(user, "link")
assert type(rv_user) is str
assert rv_user == ANCHOR

# --- trace 56: the {comment} field, same path, also unchanged -------------
rv_comment = formatter.format_field(safe_comment, "")
assert type(rv_comment) is str
assert rv_comment == "&lt;script&gt;alert(document.cookie);&lt;/script&gt;"

# --- trace 57-59: vformat joins, Markup.format wraps the result -----------
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)

EXPECTED = (
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)
assert page == EXPECTED
assert type(page) is Markup  # the wrap at __init__.py:315 restored the type
assert "<script>" not in page
assert "&amp;lt;script&amp;gt;" not in page  # the comment was not escaped twice

# --- trace 60-61: Markup.__repr__ -----------------------------------------
assert repr(page) == (
    'Markup(\'<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>')"
)

print("chapter 4 verified")
