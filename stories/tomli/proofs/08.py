"""Replay of chapter 8: the second record and the return value.

Run from the repository root with PYTHONPATH=src.
"""
import tomli
from tomli._parser import (
    Output,
    TOML_WS,
    create_list_rule,
    key_value_rule,
    parse_key_value_pair,
    parse_value,
    skip_chars,
    skip_comment,
)

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""
src = toml_str.replace("\r\n", "\n")  # what loads() parses
assert len(src) == 86

# --- Rebuild the state this chapter inherits (chapters 1-7), same calls loads makes.
out = Output()
pos, header = create_list_rule(src, 1, out)
assert (pos, header) == (12, ("players",))
assert key_value_rule(src, 13, out, header, float) == 30
assert key_value_rule(src, 31, out, header, float) == 42
out.flags.finalize_pending()
pos, header = create_list_rule(src, 44, out)
assert (pos, header) == (55, ("players",))
assert out.data.dict == {"players": [{"name": "Lehtinen", "number": 26}, {}]}

# --- Chapter 8 begins here: pos 55, header ('players',).
assert skip_chars(src, 55, TOML_WS) == 55
assert skip_comment(src, 55) == 55
assert src[55] == "\n"          # statement ends -> pos 56
assert skip_chars(src, 56, TOML_WS) == 56

# name = "Numminen"
assert parse_key_value_pair(src, 56, float, 0) == (73, ("name",), "Numminen")
# the key tuple resolves to the *last* list item, not the first
assert out.data.get_or_create_nest(("players",)) is out.data.dict["players"][-1]
assert out.data.get_or_create_nest(("players",)) == {}
assert key_value_rule(src, 56, out, header, float) == 73
assert out.data.dict["players"][-1] == {"name": "Numminen"}
assert out.data.dict["players"][0] == {"name": "Lehtinen", "number": 26}

assert skip_chars(src, 73, TOML_WS) == 73
assert skip_comment(src, 73) == 73
assert src[73] == "\n"          # -> pos 74
assert skip_chars(src, 74, TOML_WS) == 74

# number = 27: int, via RE_NUMBER, parse_float untouched
assert parse_value(src, 83, float, 0) == (85, 27)
assert type(parse_value(src, 83, float, 0)[1]) is int
assert out.data.get_or_create_nest(("players",)) == {"name": "Numminen"}
assert key_value_rule(src, 74, out, header, float) == 85

# statement tail, then the end of the document
assert skip_chars(src, 85, TOML_WS) == 85
assert skip_comment(src, 85) == 85
assert src[85] == "\n"          # -> pos 86
assert skip_chars(src, 86, TOML_WS) == 86
try:
    src[86]
except IndexError:
    pass                        # this is the loop's break condition
else:
    raise AssertionError("expected IndexError at end of document")

# --- What is handed back.
expected = {
    "players": [{"name": "Lehtinen", "number": 26}, {"name": "Numminen", "number": 27}]
}
assert out.data.dict == expected
assert type(out.data.dict) is dict
assert type(out.data.dict["players"]) is list
assert type(out.data.dict["players"][1]["number"]) is int
assert type(out.data.dict["players"][1]["name"]) is str

# The public API agrees, and each call owns its own dict.
d1 = tomli.loads(toml_str)
d2 = tomli.loads(toml_str)
assert d1 == d2 == expected
assert d1 is not d2
d1["players"].append({})        # mutable, shared with nothing
assert len(tomli.loads(toml_str)["players"]) == 2

# A header with no pairs under it is valid and yields an empty record.
assert tomli.loads("[[a]]") == {"a": [{}]}

print("chapter 8 ok")
