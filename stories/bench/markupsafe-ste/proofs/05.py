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


# Chapters 1 to 4, replayed.
untrusted_comment = "<script>alert(document.cookie);</script>"
safe_comment = escape(untrusted_comment)
assert safe_comment == "&lt;script&gt;alert(document.cookie);&lt;/script&gt;"
assert escape(safe_comment) is not None and escape(safe_comment) == safe_comment

user = User(3, 'Alice "The <b>Great</b>"')
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)
assert page == (
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)

# Chapter 5, step by step.
opening = Markup("<footer>")
assert type(opening) is Markup
assert str(opening) == "<footer>"

# Trace line 65 to 70: the plain operand is escaped.
assert Markup.escape("</p> & <script>oops</script>") == (
    "&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;"
)

# Trace line 64 to 73: safe + untrusted.
partial = opening + "</p> & <script>oops</script>"
assert type(partial) is Markup
assert str(partial) == "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;"

# Trace line 77 to 86: a Markup operand passes through unchanged.
assert str(Markup.escape(Markup("</footer>"))) == "</footer>"

# Trace line 76 to 89: safe + safe, with no second escape.
footer = partial + Markup("</footer>")
assert type(footer) is Markup
assert str(footer) == (
    "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>"
)

# Trace line 90 to 91: repr names the class.
assert repr(footer) == (
    "Markup('<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>')"
)

# The road not taken: a non-str operand without __html__ raises TypeError.
try:
    Markup("<footer>") + 42
except TypeError:
    pass
else:
    raise AssertionError("expected TypeError")

print("chapter 5 verified")
