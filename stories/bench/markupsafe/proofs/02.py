import sys

from markupsafe import EscapeFormatter
from markupsafe import Markup
from markupsafe import escape


class _Stop(Exception):
    """Marks the end of this chapter's span."""


seen = {}


class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __html_format__(self, format_spec):
        # Trace line 26: format_field reaches here with the raw spec.
        seen["spec"] = format_spec
        if format_spec == "link":
            # Trace lines 27-28: the inner template literal is wrapped, not escaped.
            inner = Markup('<a href="/user/{}">{}</a>')
            seen["inner"] = inner
            seen["id"] = self.id
            raise _Stop  # stop at the end of chapter 2's span
        elif format_spec:
            raise ValueError("Invalid format spec")
        return self.__html__()

    def __html__(self):
        return Markup('<span class="user">{0}</span>').format(self.name)


user = User(3, 'Alice "The <b>Great</b>"')

# --- escape(user) takes the __html__ branch, not the type(s) is str fast path.
assert type(user) is not str
assert hasattr(user, "__html__")
safe_user = escape(user)
assert type(safe_user) is Markup
assert safe_user == (
    '<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span>'
)
# The object's own tags survive verbatim; only the name inside them is escaped.
assert '<span class="user">' in safe_user
assert "<b>" not in safe_user
# Trace line 20: the repr printed by the scenario.
assert repr(safe_user) == (
    "Markup('<span class=\"user\">Alice &#34;The"
    " &lt;b&gt;Great&lt;/b&gt;&#34;</span>')"
)

# --- Trace lines 21-22: the template literal is wrapped, never escaped.
template = Markup("<p>User: {user:link} said: {comment}</p>")
assert type(template) is Markup
assert str(template) == "<p>User: {user:link} said: {comment}</p>"

# --- Trace line 24: the formatter stores the bound classmethod of this class.
fmt = EscapeFormatter(Markup.escape)
assert fmt.escape.__func__ is Markup.escape.__func__
assert fmt.escape.__self__ is Markup

# --- Road not taken: __html__ without __html_format__, plus a non-empty spec.
class OnlyHTML:
    def __html__(self):
        return Markup("<foo>")


try:
    EscapeFormatter(Markup.escape).format_field(OnlyHTML(), "link")
except ValueError as e:
    assert "does not define __html_format__" in str(e)
    assert "Format specifier link given" in str(e)
else:
    raise AssertionError("expected ValueError for spec without __html_format__")

# --- Road not taken: Markup rejects any non-empty spec for itself.
assert Markup("x").__html_format__("") == "x"
try:
    Markup("x").__html_format__(">10")
except ValueError as e:
    assert str(e) == "Unsupported format specification for Markup."
else:
    raise AssertionError("expected ValueError for Markup format spec")

# --- The chapter's span: format -> EscapeFormatter -> format_field -> __html_format__
safe_comment = escape("<script>alert(document.cookie);</script>")
assert safe_comment == "&lt;script&gt;alert(document.cookie);&lt;/script&gt;"

try:
    template.format(user=user, comment=safe_comment)
except _Stop:
    pass
else:
    raise AssertionError("format_field should have dispatched to __html_format__")

assert seen["spec"] == "link"
assert seen["id"] == 3
assert type(seen["inner"]) is Markup
assert str(seen["inner"]) == '<a href="/user/{}">{}</a>'

print("chapter 2 verified", file=sys.stderr)
