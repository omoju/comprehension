"""Replay the scenario up to the end of chapter 6 (trace lines 74-95).
Run from the repository root with PYTHONPATH=src."""

import tomli
from tomli import _re
from tomli._parser import (
    Flags,
    Output,
    create_list_rule,
    key_value_rule,
    make_safe_parse_float,
    parse_key_value_pair,
)

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""

# --- chapter 1: loads' own preprocessing, and the parse_float fast path -----
src = toml_str.replace("\r\n", "\n")
assert make_safe_parse_float(float) is float  # default returned unwrapped

# --- chapters 2-5, replayed to reach this chapter's entry state ------------
out = Output()
pos, header = create_list_rule(src, 1, out)
assert (pos, header) == (12, ("players",))
pos = key_value_rule(src, 13, out, header, float)
assert pos == 30
assert out.data.dict == {"players": [{"name": "Lehtinen"}]}

# --- chapter 6 enters here -------------------------------------------------
assert src[31:42] == "number = 26"
assert src[40:42] == "26"

# The two date/time regexes are tried first, and both decline.
assert _re.RE_DATETIME.match(src, 40) is None
assert _re.RE_LOCALTIME.match(src, 40) is None

# RE_NUMBER matches exactly the span the trace records.
m = _re.RE_NUMBER.match(src, 40)
assert m is not None
assert m.span() == (40, 42)
assert m.group() == "26"
# Empty 'floatpart' -> int branch, so parse_float is never called.
assert m.group("floatpart") == ""
assert _re.match_to_number(m, float) == 26

# The key/value pair as the trace reports it: (42, ('number',), 26)
p, key, value = parse_key_value_pair(src, 31, float, 0)
assert (p, key, value) == (42, ("number",), 26)
assert type(value) is int

# int(group, 0) is what makes the prefixed literals work.
assert tomli.loads("h = 0xDEADBEEF") == {"h": 3735928559}
assert tomli.loads("o = 0o755") == {"o": 493}

# --- the write, and this chapter's exit state ------------------------------
pos = key_value_rule(src, 31, out, header, float)
assert pos == 42
assert out.data.dict == {"players": [{"name": "Lehtinen", "number": 26}]}
# A scalar value freezes nothing.
assert out.flags.is_(("players", "number"), Flags.FROZEN) is False

# --- the branches not taken -------------------------------------------------
# Calendar validity comes from datetime, surfaced as a decode error.
try:
    tomli.loads("d = 2100-02-29T15:15:15Z")
    raise AssertionError("expected TOMLDecodeError")
except tomli.TOMLDecodeError as e:
    assert e.msg == "Invalid date or datetime"

# A value matching nothing at all.
try:
    tomli.loads("v = .")
    raise AssertionError("expected TOMLDecodeError")
except tomli.TOMLDecodeError as e:
    assert e.msg == "Invalid value"

# What the exception carries.
try:
    tomli.loads("number = 26 oops")
    raise AssertionError("expected TOMLDecodeError")
except tomli.TOMLDecodeError as e:
    assert isinstance(e, ValueError)
    assert e.msg == "Expected newline or end of document after a statement"
    assert (e.pos, e.lineno, e.colno) == (12, 1, 13)
    assert e.doc == "number = 26 oops"
    assert str(e) == e.msg + " (at line 1, column 13)"

# The parse_float guard raises a plain ValueError, not TOMLDecodeError.
unsafe = make_safe_parse_float(lambda s: {})
assert unsafe is not dict
try:
    unsafe("0.1")
    raise AssertionError("expected ValueError")
except ValueError as e:
    assert str(e) == "parse_float must not return dicts or lists"
    assert not isinstance(e, tomli.TOMLDecodeError)

print("chapter 6 proof OK")
