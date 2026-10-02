import os
import sys

sys.path.insert(0, os.path.abspath("src"))

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


# Chapters 1-3, replayed to reach this chapter's starting value.
safe_comment = escape("<script>alert(document.cookie);</script>")
assert safe_comment == Markup("&lt;script&gt;alert(document.cookie);&lt;/script&gt;")

user = User(3, 'Alice "The <b>Great</b>"')
anchor = user.__html_format__("link")
assert anchor == Markup(
    '<a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span></a>"
)
assert type(anchor) is Markup

# Trace 45-54: Markup.escape returns the same text, with no second escape.
escaped_anchor = Markup.escape(anchor)
assert escaped_anchor == anchor
assert escaped_anchor.__class__ is Markup
assert "&lt;a href" not in escaped_anchor
assert escaped_anchor.__html__() is escaped_anchor

# Trace 55: format_field hands a plain str back to vformat.
field = str(escaped_anchor)
assert type(field) is str
assert field == (
    '<a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span></a>"
)

# Trace 56-59: both fields render and Markup.format wraps the joined result.
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)
expected = Markup(
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)
assert page == expected
assert type(page) is Markup
assert "<script>" not in page
assert "&lt;script&gt;alert(document.cookie);&lt;/script&gt;" in page

# Trace 60-61: __repr__ names the class.
assert repr(page).startswith('Markup(\'<p>User: <a href="/user/3">')
assert repr(page).endswith("&lt;/script&gt;</p>')")
