import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from markupsafe import Markup, escape


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


# --- chapters 1-5, replayed to reach this chapter's entry value -------------
untrusted_comment = "<script>alert(document.cookie);</script>"
safe_comment = escape(untrusted_comment)
assert safe_comment == Markup("&lt;script&gt;alert(document.cookie);&lt;/script&gt;")

user = User(3, 'Alice "The <b>Great</b>"')
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)
assert page == (
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)

# trace line 92: the footer comparison literal goes through Markup.__new__
footer = Markup("<footer>") + "</p> & <script>oops</script>" + Markup("</footer>")
assert footer == Markup(
    "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>"
)

# --- chapter 6 span (trace lines 94-101) -----------------------------------

# The comment pass finds nothing: value.find("<!--") is -1, so its body never runs.
assert page.find("<!--") == -1

# trace line 95: after both passes and the whitespace collapse, striptags hands
# exactly this string to Markup.__new__ ...
stripped = (
    "User: Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    " said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;"
)
# ... and trace lines 97-98: unescape turns it back into live text.
assert Markup(stripped).unescape() == (
    'User: Alice "The <b>Great</b>" said: <script>alert(document.cookie);</script>'
)

# trace line 99: the whole call returns that plain string.
text = page.striptags()
assert text == (
    'User: Alice "The <b>Great</b>" said: <script>alert(document.cookie);</script>'
)
# The safe type is dropped on purpose: the result is a plain str, not Markup.
assert type(text) is str
assert not isinstance(text, Markup)
# The payload is live again in the plain-text view, and still inert in the page.
assert "<script>" in text
assert "<script>" not in page

# Comments are stripped before tags, so a tag inside a comment cannot end it early.
assert Markup("<!-- <em> -->x").striptags() == "x"
# Unterminated markers make the loop break; the remainder is left as-is.
assert Markup("a<!--b").striptags() == "a<!--b"

# trace lines 100-101: Markup() over a developer-written literal, then compare.
expected = Markup(
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)
assert page == expected
assert type(page) is Markup

# The edge helpers named in the callout.
from markupsafe import escape_silent, soft_str  # noqa: E402

assert escape(None) == Markup("None")
assert escape_silent(None) == Markup("")
assert type(soft_str(page)) is Markup
assert type(soft_str(15)) is str
