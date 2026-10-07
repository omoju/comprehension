"""Replays the scenario up to the end of chapter 3's span.

Run from the repository root with PYTHONPATH=src.
"""
from tomli._parser import (
    Flags,
    Output,
    TOMLDecodeError,
    create_dict_rule,
    create_list_rule,
    skip_chars,
    skip_comment,
    TOML_WS,
)
import tomli

src = (
    '\n[[players]]\nname = "Lehtinen"\nnumber = 26\n'
    '\n[[players]]\nname = "Numminen"\nnumber = 27\n'
)
# loads() normalizes CRLF; this document has none, so src is what the parser sees.
assert tomli.loads(src)["players"][0]["name"] == "Lehtinen"

# --- the world the key enters: a fresh Output, empty on both sides ---
out = Output()
assert out.data.dict == {}
assert out.flags.is_(("players",), Flags.FROZEN) is False
assert out.flags.is_(("players",), Flags.EXPLICIT_NEST) is False

# --- chapter 3's span: create_list_rule from pos=1 (the first '[') ---
assert src[1] == "[" and src[2] == "["
pos, header = create_list_rule(src, 1, out)

# returns the cursor just past "]]", plus the key tuple
assert (pos, header) == (12, ("players",))

# one empty record has been appended under 'players'
assert out.data.dict == {"players": [{}]}

# the key is now claimed against [table] syntax, but is not frozen
assert out.flags.is_(("players",), Flags.EXPLICIT_NEST) is True
assert out.flags.is_(("players",), Flags.FROZEN) is False

# --- the statement tail: whitespace, comment, mandatory newline ---
assert skip_chars(src, pos, TOML_WS) == 12
assert skip_comment(src, 12) == 12          # src[12] is '\n', not '#'
assert src[12] == "\n"
pos += 1                                     # loads() does this at line 230
assert skip_chars(src, pos, TOML_WS) == 13   # loop top, nothing to skip
assert src[13] == "n"                        # poised on `name`

# --- the branch not taken: [players] would now be refused ---
try:
    create_dict_rule("[players]", 0, out)
except TOMLDecodeError as e:
    assert e.msg == "Cannot declare ('players',) twice"
else:
    raise AssertionError("expected a duplicate-declaration error")

# ...while a second [[players]] is accepted and appends another record
pos2, header2 = create_list_rule(src, 44, out)
assert (pos2, header2) == (55, ("players",))
assert out.data.dict == {"players": [{}, {}]}

# --- KeyError from the nested dict surfaces as TOMLDecodeError ---
try:
    tomli.loads("a=true\n[[a]]\n")
except TOMLDecodeError as e:
    assert e.msg == "Cannot overwrite a value"
else:
    raise AssertionError("expected an overwrite error")

# --- the closing "]]" is verified, not assumed ---
try:
    tomli.loads("[[a]\nb=2\n")
except TOMLDecodeError as e:
    assert e.msg == "Expected ']]' at the end of an array declaration"
else:
    raise AssertionError("expected a missing-bracket error")

print("chapter 3 proof OK")
