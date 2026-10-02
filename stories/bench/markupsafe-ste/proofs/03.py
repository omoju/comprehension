"""Replay the run up to the end of chapter 3.

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


# Chapter 1: the escaped comment is still held beside the user.
safe_comment = escape("<script>alert(document.cookie);</script>")
assert safe_comment == Markup("&lt;script&gt;alert(document.cookie);&lt;/script&gt;")

name = 'Alice "The <b>Great</b>"'
user = User(3, name)

# The innermost field: a plain str with an empty spec takes the default branch.
formatter = EscapeFormatter(Markup.escape)
rv = formatter.format_field(name, "")
assert rv == "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
# format_field hands back a plain str; the safe type is stripped here.
assert type(rv) is str
assert not isinstance(rv, Markup)

# Markup.escape produces the same text, typed as Markup.
esc = Markup.escape(name)
assert esc == Markup("Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;")
assert type(esc) is Markup

# Markup.format wraps the joined text again.
span = user.__html__()
assert span == Markup(
    '<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span>'
)
assert type(span) is Markup

# The two fields of the anchor template.
assert formatter.format_field(3, "") == "3"
assert formatter.format_field(span, "") == (
    '<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span>'
)

# The value that leaves this chapter.
link = user.__html_format__("link")
assert link == Markup(
    '<a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a>"
)
assert type(link) is Markup
print("chapter 3 proof ok")
