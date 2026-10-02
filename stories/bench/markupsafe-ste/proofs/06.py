import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from markupsafe import Markup, escape, escape_silent, soft_str


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


# Chapters 1-4: escape the comment, then render the page.
safe_comment = escape("<script>alert(document.cookie);</script>")
assert safe_comment == Markup("&lt;script&gt;alert(document.cookie);&lt;/script&gt;")

user = User(3, 'Alice "The <b>Great</b>"')
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)
expected = Markup(
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)
assert page == expected
assert isinstance(page, Markup)

# Chapter 5: concatenation escapes the plain operand only.
footer = Markup("<footer>") + "</p> & <script>oops</script>" + Markup("</footer>")
assert footer == Markup(
    "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>"
)

# Chapter 6: record the value that striptags hands to unescape (trace line 95).
seen = []
original_unescape = Markup.unescape


def recording_unescape(self):
    seen.append(str(self))
    return original_unescape(self)


Markup.unescape = recording_unescape
try:
    text = page.striptags()
finally:
    Markup.unescape = original_unescape

assert seen == [
    "User: Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    " said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;"
]

# The value that leaves striptags: plain str, entities gone (trace lines 98-99).
assert text == (
    'User: Alice "The <b>Great</b>" said: <script>alert(document.cookie);</script>'
)
assert type(text) is str
assert "<script>" in text

# The page itself did not change; the scenario's final checks hold.
assert "<script>" not in page
assert page == expected

# striptags is best-effort: an unterminated marker leaves the rest in place.
assert Markup("a<!-- b").striptags() == "a<!-- b"
assert Markup("a<b").striptags() == "a<b"

# Helpers at the edge.
assert escape(None) == Markup("None")
assert escape_silent(None) == Markup("")
assert type(soft_str(Markup("<b>"))) is Markup
assert type(soft_str(15)) is str
