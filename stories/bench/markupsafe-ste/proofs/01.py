"""Chapter 1: escape() of an untrusted comment, and the idempotent second pass.

Run from the repository root with PYTHONPATH=src.
"""

from markupsafe import Markup, escape
from markupsafe import _escape_inner

# --- the data enters as a plain str -------------------------------------
untrusted_comment = "<script>alert(document.cookie);</script>"
assert type(untrusted_comment) is str  # takes the fast path at __init__.py:39

# --- escape() -> _escape_inner -> Markup.__new__ ------------------------
safe_comment = escape(untrusted_comment)
assert type(safe_comment) is Markup
assert safe_comment == "&lt;script&gt;alert(document.cookie);&lt;/script&gt;"

# _escape_inner replaces exactly five characters, and '&' first.
assert _escape_inner("&><'\"") == "&amp;&gt;&lt;&#39;&#34;"
assert _escape_inner("a=b `c` \n") == "a=b `c` \n"

# Markup.__new__ does not escape; it only marks text as safe.
assert str(Markup("<script>")) == "<script>"

# --- Markup.__repr__ ----------------------------------------------------
assert repr(safe_comment) == (
    "Markup('&lt;script&gt;alert(document.cookie);&lt;/script&gt;')"
)

# --- second pass: the __html__ branch, escaping is idempotent -----------
again = escape(safe_comment)
assert type(again) is Markup
assert again == safe_comment
assert safe_comment.__html__() is safe_comment  # Markup.__html__ returns self

# escape() calls __html__ once; a plain str result is not asked again.
class Plain:
    calls = 0

    def __html__(self):
        Plain.calls += 1
        return "<b>safe</b>"

assert escape(Plain()) == Markup("<b>safe</b>")
assert Plain.calls == 1

# Markup.__new__ calls __html__ on the value that escape() received back.
class Inner:
    calls = 0

    def __html__(self):
        Inner.calls += 1
        return "<b>safe</b>"

class Outer:
    def __html__(self):
        return Inner()

assert escape(Outer()) == Markup("<b>safe</b>")
assert Inner.calls == 1  # this call came from Markup.__new__, not from escape

# The third branch: str(s) then escape. escape(None) gives Markup('None').
assert escape(None) == Markup("None")

print("chapter 1 proof ok")
