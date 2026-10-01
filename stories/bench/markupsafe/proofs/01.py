"""Chapter 1: escape() of an untrusted comment, and the idempotent round trip.

Run from the repository root with PYTHONPATH=src.
"""

from markupsafe import Markup, escape
from markupsafe import _native

UNTRUSTED = "<script>alert(document.cookie);</script>"
ESCAPED = "&lt;script&gt;alert(document.cookie);&lt;/script&gt;"

# --- trace line 2-5: escape() takes the exact-str fast path and wraps in Markup.
assert type(UNTRUSTED) is str  # the condition at __init__.py:39
safe_comment = escape(UNTRUSTED)
assert safe_comment == ESCAPED, safe_comment
assert type(safe_comment) is Markup

# The replacement itself: exactly five characters, ampersand first.
assert _native._escape_inner(UNTRUSTED) == ESCAPED
assert _native._escape_inner("\"<>&'") == "&#34;&lt;&gt;&amp;&#39;"
# Nothing else is touched: backtick, '=' and whitespace survive.
assert _native._escape_inner("a `b` = c") == "a `b` = c"

# --- trace line 6-7: __repr__ names the class.
assert repr(safe_comment) == (
    "Markup('&lt;script&gt;alert(document.cookie);&lt;/script&gt;')"
)

# --- trace line 8-9: the constructor escapes nothing; it only asserts safety.
assert Markup(ESCAPED) == ESCAPED
assert Markup("<b>unchecked</b>") == "<b>unchecked</b>"  # the unguarded door

# --- trace line 10-17: escaping an already-safe value is a no-op.
assert type(safe_comment) is not str  # so the fast path at :39 is refused
assert hasattr(safe_comment, "__html__")  # the branch at :42 wins
assert safe_comment.__html__() is safe_comment  # :133-134 returns self
again = escape(safe_comment)
assert again == safe_comment == ESCAPED
assert "&amp;lt;" not in again  # not double-escaped

# The two __html__ calls in the trace (lines 11-12 and 14-15): escape() calls it,
# then Markup.__new__ checks the *result* for __html__ and calls it again.
calls = []


class Counting(Markup):
    def __html__(self):
        calls.append(1)
        return self


escape(Counting("x"))
assert len(calls) == 2, calls

# Road not taken, shown for contrast: None has no __html__ and is not a str.
assert escape(None) == Markup("None")

print("chapter 1 ok")
