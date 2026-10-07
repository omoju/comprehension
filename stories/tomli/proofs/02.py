import sys
from tomli._parser import (
    BARE_KEY_CHARS,
    MAX_KEY_PARTS,
    TOML_WS,
    parse_key,
    parse_key_part,
    skip_chars,
)

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""

# Chapter 1 left the data here: the CRLF rewrite is a no-op for this document,
# and the cursor sits on the first "[" of "[[players]]".
src = toml_str.replace("\r\n", "\n")
assert src == toml_str
assert src[1] == "[" and src[2] == "["

# create_list_rule: pos += 2 skips "[[", then whitespace (there is none).
pos = 1 + 2
assert pos == 3
assert skip_chars(src, pos, TOML_WS) == 3

# parse_key_part takes the bare-key road: "p" is in BARE_KEY_CHARS,
# and the walk stops at index 10, where "]" begins.
assert src[3] in BARE_KEY_CHARS
assert skip_chars(src, 3, BARE_KEY_CHARS) == 10
assert parse_key_part(src, 3) == (10, "players")

# Trailing whitespace skip is a no-op; src[10] is "]" not ".", so the
# dotted-key loop ends immediately and parse_key returns a 1-tuple.
assert skip_chars(src, 10, TOML_WS) == 10
assert src[10] == "]"
assert parse_key(src, 3) == (10, ("players",))

# The road not taken: a dot continues the loop and grows the tuple.
assert parse_key("a . b.c]", 0) == (7, ("a", "b", "c"))

# The guard on that loop is process-wide, read from the recursion limit.
assert MAX_KEY_PARTS == sys.getrecursionlimit()

print("chapter 2 ok")
