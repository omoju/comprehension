"""Replays the scenario through chapter 3: the user's name escaped into the span,
and the completed anchor returned by __html_format__."""

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


# Chapters 1-2: the untrusted comment, and the user object's own markup.
safe_comment = escape("<script>alert(document.cookie);</script>")
assert safe_comment == "&lt;script&gt;alert(document.cookie);&lt;/script&gt;", safe_comment

user = User(3, 'Alice "The <b>Great</b>"')

# trace 33-40: the name has no __html_format__/__html__, so format_field renders it
# with the stdlib and escapes the result -- returning a bare str, not a Markup.
formatter = EscapeFormatter(Markup.escape)
rv = formatter.format_field(user.name, "")
assert rv == "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;", rv
assert type(rv) is str, type(rv)

# trace 35-39: escape() on that same plain str, via Markup.escape.
inner = escape(user.name)
assert inner == "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;", inner
assert type(inner) is Markup, type(inner)

# trace 30-43: Markup.format reinstates the safe type on the joined span.
span = user.__html__()
assert span == Markup(
    '<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span>'
), span
assert type(span) is Markup, type(span)

# trace 44 (elided), field 1: an int goes the same route as the name and escapes to itself.
assert formatter.format_field(user.id, "") == "3"

# trace 44 (elided), field 2: a Markup field takes the __html_format__ door and,
# with an empty spec, is handed back unchanged -- same object.
assert span.__html_format__("") is span

# trace 44 (elided): the completed anchor leaving User.__html_format__.
anchor = user.__html_format__("link")
assert anchor == Markup(
    '<a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a>"
), anchor
assert type(anchor) is Markup, type(anchor)

# The live tags are the template's; the name's brackets are inert.
assert "<b>" not in anchor
assert "&lt;b&gt;" in anchor

print("chapter 3 verified")
