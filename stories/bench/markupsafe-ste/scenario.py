"""Render a small HTML page fragment safely, as shown in MarkupSafe's README/docs."""

import os
import sys

# Make the repository's package importable when running from the repo root.
_src = os.path.abspath("src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

from markupsafe import Markup  # noqa: E402
from markupsafe import escape  # noqa: E402


class User:
    """A user whose name is escaped, from docs/formatting.rst."""

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


# 1. Untrusted input arrives (e.g. a comment posted on a page).
untrusted_comment = "<script>alert(document.cookie);</script>"
safe_comment = escape(untrusted_comment)
print(repr(safe_comment))
assert safe_comment == Markup("&lt;script&gt;alert(document.cookie);&lt;/script&gt;")

# Escaping is idempotent: already-safe markup passes through unchanged.
assert escape(safe_comment) == safe_comment

# 2. A user object that knows its own HTML representation.
user = User(3, 'Alice "The <b>Great</b>"')
print(repr(escape(user)))

# 3. Format both into a Markup template; arguments are escaped as needed.
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)
print(repr(page))

# 4. Concatenation with plain text still escapes the plain text.
footer = Markup("<footer>") + "</p> & <script>oops</script>" + Markup("</footer>")
print(repr(footer))
assert footer == Markup(
    "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>"
)

# 5. The plain-text view of the rendered fragment.
text = page.striptags()
print(text)
assert text == (
    'User: Alice "The <b>Great</b>" said: <script>alert(document.cookie);</script>'
)

expected = Markup(
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)
assert page == expected, page
assert isinstance(page, Markup)
assert "<script>" not in page
