"""Chapter 1: across the trust boundary. Run from repo root with PYTHONPATH=src."""
import sys

import tomli
from tomli import _parser

toml_str = """
[[players]]
name = "Lehtinen"
number = 26

[[players]]
name = "Numminen"
number = 27
"""

# --- the protagonist, exactly as the caller hands it over ---
assert toml_str.startswith('\n[[players]]\nname = "Lehtinen"\nnumber = 26\n')
assert toml_str.endswith('\n[[players]]\nname = "Numminen"\nnumber = 27\n')

# The CRLF -> LF rewrite is a no-op for this document: src == __s.
src = toml_str.replace("\r\n", "\n")
assert src == toml_str
assert "\r" not in src

# --- the type check lives in that same replace() call ---
for bad, qualname in ((b"v = 1", "bytes"), (False, "bool")):
    try:
        tomli.loads(bad)
    except TypeError as e:
        # Pure Python raises this message; the mypyc build words it differently.
        assert str(e) in (
            f"Expected str object, not '{qualname}'",
            f"str object expected; got {qualname}",
        ), str(e)
    else:
        raise AssertionError("expected TypeError")

# --- the world the string is about to enter, built fresh and empty ---
out = _parser.Output()
assert out.data.dict == {}
assert out.flags._flags == {}
assert out.flags._pending_flags == set()
# No shared state: a second Output is a different object with a different dict.
assert out.data.dict is not _parser.Output().data.dict

header = ()
pos = 0

# --- parse_float: the default is handed back unwrapped ---
assert _parser.make_safe_parse_float(float) is float
# Any other callable gets the dict/list guard wrapped around it.
wrapped = _parser.make_safe_parse_float(lambda s: {})
assert wrapped is not float
try:
    wrapped("0.1")
except ValueError as e:
    assert str(e) == "parse_float must not return dicts or lists"
else:
    raise AssertionError("expected ValueError")
# ... and that guard fires through the public API too.
try:
    tomli.loads("f=0.1", parse_float=lambda s: [])
except ValueError as e:
    assert str(e) == "parse_float must not return dicts or lists"
else:
    raise AssertionError("expected ValueError")

# --- first two turns of the statement loop ---
pos = _parser.skip_chars(src, pos, _parser.TOML_WS)
assert pos == 0                      # trace line 11-12
assert src[pos] == "\n"
pos += 1                             # the leading newline is consumed
pos = _parser.skip_chars(src, pos, _parser.TOML_WS)
assert pos == 1                      # the elided second skip_chars

assert src[pos] == "["
assert src[pos + 1] == "["           # second_char -> create_list_rule, not create_dict_rule

assert out.flags.finalize_pending() is None   # trace line 14-15: a no-op here
assert out.flags._pending_flags == set()
assert out.data.dict == {}           # nothing written yet

# --- the chapter ends exactly where chapter 2 picks up ---
assert (pos, header) == (1, ())
print("chapter 1 ok")
