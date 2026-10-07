"""Replay tomli's parse of the README example up to the end of chapter 5's span.

Run from the repository root with PYTHONPATH=src.
"""
from tomli._parser import (
    Flags,
    Output,
    TOML_WS,
    TOMLDecodeError,
    create_list_rule,
    key_value_rule,
    skip_chars,
    skip_comment,
)
import tomli

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""

src = toml_str.replace("\r\n", "\n")
assert src is not toml_str or "\r\n" not in src  # loads normalizes CRLF first
assert src[13:30] == 'name = "Lehtinen"'

# ---- state as it stood at the end of chapter 3 -------------------------------
out = Output()
pos, header = create_list_rule(src, 1, out)
assert (pos, header) == (12, ("players",))
assert out.data.dict == {"players": [{}]}

pos = skip_chars(src, pos, TOML_WS)
pos = skip_comment(src, pos)
assert pos == 12 and src[pos] == "\n"
pos += 1
pos = skip_chars(src, pos, TOML_WS)
assert pos == 13  # cursor on 'name'

# ---- chapter 5 span: trace lines 63-73 ---------------------------------------

# trace 63-64: the namespace is not frozen, so the write is permitted.
assert out.flags.is_(header, Flags.FROZEN) is False
# ...but it *is* claimed as an explicit nest by the [[players]] header.
assert out.flags.is_(header, Flags.EXPLICIT_NEST) is True

# trace 65-66: get_or_create_nest descends into the LAST list item, and returns
# the very dict already living in the output tree (not a copy).
nest = out.data.get_or_create_nest(header)
assert nest == {}
assert nest is out.data.dict["players"][-1]

# trace 67: the value lands in that dict; key_value_rule returns the new cursor.
pos = key_value_rule(src, 13, out, header, float)
assert pos == 30
assert out.data.dict == {"players": [{"name": "Lehtinen"}]}
assert out.data.dict["players"][0] is nest
assert isinstance(out.data.dict["players"][0]["name"], str)
# A str value sets no FROZEN flag (the isinstance(dict, list) branch not taken).
assert out.flags.is_(header + ("name",), Flags.FROZEN) is False

# trace 68-73: the statement tail, then the top of the next loop iteration.
assert skip_chars(src, pos, TOML_WS) == 30
assert skip_comment(src, pos) == 30
assert src[pos] == "\n"
pos += 1
assert skip_chars(src, pos, TOML_WS) == 31
assert src[31:42] == "number = 26"

# ---- the branches this run did not take, via the public API ------------------
# Duplicate key in the same table: rejected, not overwritten.
try:
    tomli.loads('name = "Tom"\nname = "Pradyun"\n')
except TOMLDecodeError as e:
    assert e.msg == "Cannot overwrite a value", e.msg
else:
    raise AssertionError("duplicate key was accepted")

# A dict value freezes its namespace recursively.
try:
    tomli.loads("a = { b = 1 }\na.b = 2\n")
except TOMLDecodeError as e:
    assert e.msg == "Cannot mutate immutable namespace ('a',)", e.msg
else:
    raise AssertionError("inline table was mutated")

# A non-dict in the key path becomes a decode error, not a bare KeyError.
try:
    tomli.loads("a=1\n[a.b.c.d]\n")
except TOMLDecodeError as e:
    assert e.msg == "Cannot overwrite a value", e.msg
else:
    raise AssertionError("value was overwritten by a table")

print("chapter 5 proof OK")
