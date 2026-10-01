"""Replay the scenario through the footer concatenation (trace lines 1-91)."""

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


# --- Chapters 1-4, so the footer starts from the same world ---------------
untrusted_comment = "<script>alert(document.cookie);</script>"
safe_comment = escape(untrusted_comment)
assert safe_comment == "&lt;script&gt;alert(document.cookie);&lt;/script&gt;"
assert escape(safe_comment) == safe_comment  # idempotent

user = User(3, 'Alice "The <b>Great</b>"')
template = Markup("<p>User: {user:link} said: {comment}</p>")
page = template.format(user=user, comment=safe_comment)
assert page == (
    '<p>User: <a href="/user/3"><span class="user">'
    "Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;"
    "</span></a> said: &lt;script&gt;alert(document.cookie);&lt;/script&gt;</p>"
)
assert type(page) is Markup

# --- Chapter 5: trace lines 62-91 ----------------------------------------
# line 62: the literal is wrapped, not escaped.
opening = Markup("<footer>")
assert opening == "<footer>"

# lines 64-70: __add__ escapes the plain-str operand via Markup.escape.
payload = "</p> & <script>oops</script>"
escaped_payload = Markup.escape(payload)
assert escaped_payload == "&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;"
assert type(escaped_payload) is Markup
# The bare "&" became "&amp;" exactly once -- no double escaping.
assert "&amp;amp;" not in escaped_payload

# lines 71-73: the intermediate value.
partial = opening + payload
assert partial == "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;"
assert type(partial) is Markup

# lines 77-86: escaping an already-safe operand changes nothing.
closing = Markup("</footer>")
assert Markup.escape(closing) == "</footer>"
assert closing.__html__() is closing

# lines 87-91: the finished footer and its repr.
footer = partial + closing
assert footer == "<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>"
assert type(footer) is Markup
assert repr(footer) == (
    "Markup('<footer>&lt;/p&gt; &amp; &lt;script&gt;oops&lt;/script&gt;</footer>')"
)

# --- Roads not taken, asserted so the story's claims can fail -------------
# A non-str, non-__html__ operand is refused rather than stringified.
assert Markup("a").__add__(3) is NotImplemented
try:
    Markup("a") + 3
except TypeError:
    pass
else:
    raise AssertionError("expected TypeError for Markup + int")

# __radd__: a plain str on the left is escaped too.
assert "</p>" + Markup("<footer>") == "&lt;/p&gt;<footer>"

# Search-style methods do NOT escape their argument; insertion-style do.
assert Markup("<a>x</a>").replace("x", "<b>") == "<a>&lt;b&gt;</a>"
assert Markup("-").join(["<a>", Markup("<b>")]) == "&lt;a&gt;-<b>"
assert Markup("xa x").removeprefix("x") == "a x"

# Slicing a Markup can cut an entity in half and still return Markup.
sliced = escaped_payload[:7]
assert sliced == "&lt;/p&"
assert type(sliced) is Markup

print("chapter 5 verified")
