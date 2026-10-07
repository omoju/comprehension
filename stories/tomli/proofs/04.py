import sys

sys.path.insert(0, "src")

from tomli import _parser as p

src = (
    '\n[[players]]\nname = "Lehtinen"\nnumber = 26\n'
    '\n[[players]]\nname = "Numminen"\nnumber = 27\n'
)

# Chapters 1-3 in brief: the first [[players]] header, leaving pos=13.
out = p.Output()
assert p.create_list_rule(src, 1, out) == (12, ("players",))
assert out.data.dict == {"players": [{}]}
assert src[12] == "\n"
pos = 13
assert src[pos] == "n" and src[pos] in p.KEY_INITIAL_CHARS

# --- Chapter 4's span: pos 13 -> (30, ('name',), 'Lehtinen') ---

# parse_key_part reads the bare key.
assert p.parse_key_part(src, 13) == (17, "name")
# parse_key skips the space after it and stops on '=' (no dotted parts).
assert p.parse_key(src, 13) == (18, ("name",))
assert src[18] == "="

# parse_key_value_pair steps past '=' and the space before the value.
assert p.skip_chars(src, 19, p.TOML_WS) == 20
assert src[20] == '"'
# Not a multiline string: the three-quote test fails.
assert not src.startswith('"""', 20)

# The value is produced by the single-line basic string path.
assert p.parse_basic_str(src, 21, multiline=False) == (30, "Lehtinen")
assert p.parse_one_line_basic_str(src, 20) == (30, "Lehtinen")
assert p.parse_value(src, 20, float, 0) == (30, "Lehtinen")

# The whole span, as key_value_rule calls it.
result = p.parse_key_value_pair(src, 13, float, nest_lvl=0)
assert result == (30, ("name",), "Lehtinen")
assert type(result[2]) is str

# The nesting bound carried in nest_lvl, and the illegal-character alphabet.
assert p.MAX_INLINE_NESTING == 400
assert "\n" in p.ILLEGAL_BASIC_STR_CHARS and "\t" not in p.ILLEGAL_BASIC_STR_CHARS

# Branches not taken on this road.
try:
    p.parse_key_value_pair('a 1', 0, float, nest_lvl=0)
except p.TOMLDecodeError as e:
    assert e.msg == "Expected '=' after a key in a key/value pair"
else:
    raise AssertionError("missing '=' must raise")

try:
    p.parse_basic_str('unterminated', 0, multiline=False)
except p.TOMLDecodeError as e:
    assert e.msg == "Unterminated string"
else:
    raise AssertionError("unterminated string must raise")

# Escaped control characters, however, are accepted into the result.
assert p.parse_value('"\\u0000"', 0, float, 0) == (8, "\x00")

print("chapter 4 ok")
