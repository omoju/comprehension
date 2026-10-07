"""Replay the scenario through chapter 7's span (trace lines 96-126)."""
import tomli
from tomli import _parser as p

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""

# --- Chapter 1 setup -------------------------------------------------------
src = toml_str.replace("\r\n", "\n")
assert src == toml_str  # no CRLF in this document
out = p.Output()
header = ()
parse_float = p.make_safe_parse_float(float)
assert parse_float is float

# --- Chapters 2-6, condensed: the first record ----------------------------
pos = p.skip_chars(src, 0, p.TOML_WS)
assert pos == 0 and src[pos] == "\n"
pos += 1

assert src[pos] == "[" and src[pos + 1] == "["
out.flags.finalize_pending()
pos, header = p.create_list_rule(src, pos, out)
assert (pos, header) == (12, ("players",))

for expected_end in (30, 42):
    pos = p.skip_chars(src, pos, p.TOML_WS)
    pos = p.skip_comment(src, pos)
    assert src[pos] == "\n"
    pos += 1
    pos = p.skip_chars(src, pos, p.TOML_WS)
    pos = p.key_value_rule(src, pos, out, header, parse_float)
    assert pos == expected_end

assert out.data.dict == {"players": [{"name": "Lehtinen", "number": 26}]}

# --- Chapter 7 span begins: trace lines 96-102 ----------------------------
pos = p.skip_chars(src, pos, p.TOML_WS)
assert pos == 42
pos = p.skip_comment(src, pos)
assert pos == 42
assert src[pos] == "\n"
pos += 1  # 43

pos = p.skip_chars(src, pos, p.TOML_WS)
assert pos == 43
assert src[pos] == "\n"  # the blank line: `continue`, no comment scan
pos += 1  # 44

pos = p.skip_chars(src, pos, p.TOML_WS)
assert pos == 44

# --- trace lines 103-126: the second [[players]] header -------------------
assert src[pos] == "[" and src[pos + 1] == "["
assert out.flags._pending_flags == set()  # finalize_pending is a no-op here
out.flags.finalize_pending()

# what create_list_rule sees on the way through
assert p.skip_chars(src, 46, p.TOML_WS) == 46
assert p.parse_key(src, 46) == (53, ("players",))
assert out.flags.is_(("players",), p.Flags.FROZEN) is False
assert out.flags.is_(("players",), p.Flags.EXPLICIT_NEST) is True
assert out.data.get_or_create_nest(()) is out.data.dict
assert out.data.dict == {"players": [{"name": "Lehtinen", "number": 26}]}

pos, header = p.create_list_rule(src, pos, out)
assert (pos, header) == (55, ("players",))
assert out.data.dict == {
    "players": [{"name": "Lehtinen", "number": 26}, {}]
}
assert out.data.dict["players"][-1] == {}
# the name is re-claimed against table syntax, and still not frozen
assert out.flags.is_(("players",), p.Flags.EXPLICIT_NEST) is True
assert out.flags.is_(("players",), p.Flags.FROZEN) is False

# --- the branches the data did not take -----------------------------------
# [[array]] may repeat; [table] may not, in either order.
assert tomli.loads("[[a]]\n[[a]]\n") == {"a": [{}, {}]}
for bad in ("[[a]]\n[a]\n", "[a]\n[[a]]\n", "[a]\n[a]\n"):
    try:
        tomli.loads(bad)
    except tomli.TOMLDecodeError as e:
        assert "Cannot declare" in e.msg or "Cannot overwrite" in e.msg, e.msg
    else:
        raise AssertionError(f"expected TOMLDecodeError for {bad!r}")

# unset_all frees dotted-key containers for the next list item...
assert tomli.loads("[[a]]\nb.c = 1\n[[a]]\nb.c = 2\n") == {
    "a": [{"b": {"c": 1}}, {"b": {"c": 2}}]
}
# ...while pending flags let siblings share a prefix, then close it.
assert tomli.loads("[a]\nb.c = 1\nb.d = 2\n") == {"a": {"b": {"c": 1, "d": 2}}}
try:
    tomli.loads("[t1]\nt2.t3.v = 0\n[t1.t2]\n")
except tomli.TOMLDecodeError as e:
    assert "Cannot declare" in e.msg, e.msg
else:
    raise AssertionError("expected TOMLDecodeError for finalized pending flag")

# a non-list behind the name becomes a decode error, not a KeyError
try:
    tomli.loads("a=true\n[[a]]\n")
except tomli.TOMLDecodeError as e:
    assert e.msg == "Cannot overwrite a value", e.msg
else:
    raise AssertionError("expected TOMLDecodeError for overwritten value")

print("chapter 7 verified")
