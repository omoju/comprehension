# Chapter 6 · When the value is not a string: regexes, lazily

> **Enters as:** `pos = 31`, `header = ('players',)`, `out.data.dict == {'players': [{'name': 'Lehtinen'}]}` — the cursor on the `n` of `number = 26`

The second statement of the record travels the same road as the first. `key_value_rule` hands straight off to `parse_key_value_pair` ([`_parser.py#L431`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L431)), `parse_key` consumes six bare-key characters and returns `(37, 'number')`, a `skip_chars` eats the space to 38, where the `=` sits; `pos` steps to 39 and another `skip_chars` lands on 40 ([`_parser.py#L465-L474`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L465-L474)). The trace records exactly that: `(38, ('number',))`, then `skip_chars(pos=39) → 40`.

What is different starts here. At position 40 sits `2`, and `parse_value` has no fast character test for digits.

### The dispatch runs out of cheap options

`parse_value` is ordered deliberately — "IMPORTANT: order conditions based on speed of checking and likelihood" ([`_parser.py#L719`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L719)). A `"` or `'` is a string, `t`/`f` a boolean, `[` an array, `{` an inline table; each is a single comparison ([`_parser.py#L721-L747`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L721-L747)). A `2` is none of them, so the value falls through to the only part of the parser that needs regular expressions.

That fall-through is the reason the regexes exist in a separate module at all. `_parser.py` opens by declaring it:

```
# Defer loading regular expressions until we actually need them in
# parse_value().
__lazy_modules__ = ["tomli._re"]
```

([`_parser.py#L7-L9`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L7-L9)), and only then writes the ordinary-looking `from ._re import (...)` ([`_parser.py#L13-L20`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L13-L20)). On an interpreter that honours the declaration, importing `tomli` does not pay for `re` and `datetime`; a document made only of strings, booleans and arrays never touches them. The repository checks this directly — a subprocess parses such a document and asserts `'tomli._re' not in sys.modules`, under pure Python 3.15+ ([`tests/test_misc.py#L160-L180`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/test_misc.py#L160-L180)). Our `26` is precisely the kind of value that ends that deferral.

### Dates first, and why the order is not negotiable

Before the number regex gets a look, two others are tried:

```
datetime_match = RE_DATETIME.match(src, pos)
...
localtime_match = RE_LOCALTIME.match(src, pos)
```

([`_parser.py#L749-L759`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L749-L759)). `RE_DATETIME` wants four digits then `-` ([`_re.py#L46-L56`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_re.py#L46-L56)); `RE_LOCALTIME` wants `[01][0-9]` or `2[0-3]` then `:` ([`_re.py#L17-L24`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_re.py#L17-L24)). `26` satisfies neither, and the trace shows no `match_to_datetime` or `match_to_localtime` call. The ordering is documented where it matters: "The regex will greedily match any type starting with a decimal char, so needs to be located after handling of dates and times" ([`_parser.py#L761-L763`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L761-L763)). Run `RE_NUMBER` first and `1987-07-05` would parse as the integer `1987` with trailing garbage.

Had the date branch been taken, note where validity is decided. The regex only constrains shape — month `01`–`12`, day up to `31`. The calendar is enforced by `datetime` itself, when `match_to_datetime` calls `date(...)` or `datetime(...)` ([`_re.py#L78-L92`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_re.py#L78-L92)), and `parse_value` catches the resulting `ValueError` and re-raises it as `TOMLDecodeError("Invalid date or datetime", src, pos)` ([`_parser.py#L752-L755`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L752-L755)). `2100-02-29` is therefore rejected as a decode error with a position, not as a stray `ValueError` from the standard library.

### One match, two possible types

```
number_match = RE_NUMBER.match(src, pos)
if number_match:
    return number_match.end(), match_to_number(number_match, parse_float)
```

([`_parser.py#L764-L766`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L764-L766)). The trace shows the match object: `<re.Match span=(40, 42) match='26'>`. `RE_NUMBER` covers hex/octal/binary prefixes and the decimal form in one pattern, with the fractional and exponent parts captured in a named group ([`_re.py#L26-L44`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_re.py#L26-L44)). That group is the whole of the int/float decision:

```
def match_to_number(match: re.Match[str], parse_float: ParseFloat) -> Any:
    if match.group("floatpart"):
        return parse_float(match.group())
    return int(match.group(), 0)
```

([`_re.py#L116-L119`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_re.py#L116-L119)). For `26` the group matched the empty string — falsy — so `parse_float` is never called and `int('26', 0)` runs instead. Base `0` is what lets `0xDEADBEEF`, `0o755` and `0b1101` come back as integers without a second code path; the regex has already guaranteed the literal is well-formed, including the underscores Python's `int` also accepts. The trace: `match_to_number(...) → 26`, and `parse_value` returns `(42, 26)`.

Nothing bounds how many digits that literal may have, which is worth remembering for untrusted input; the subject returns in chapter 8.

Had the regexes all failed, three characters would have been compared against `inf` and `nan`, then four against the signed forms ([`_parser.py#L768-L774`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L768-L774)), and failing that the value would have been rejected: `raise TOMLDecodeError("Invalid value", src, pos)` ([`_parser.py#L776`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L776)).

### The `parse_float` seam

This is the one place a caller's own code could have run inside the parser, and it is also where chapter 1's unwrapped `float` is explained. `make_safe_parse_float` short-circuits the default — "The default `float` callable never returns illegal types. Optimize it." ([`_parser.py#L791-L793`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L791-L793)) — and wraps anything else:

```
float_value = parse_float(float_str)
if isinstance(float_value, (dict, list)):
    raise ValueError("parse_float must not return dicts or lists")
```

([`_parser.py#L795-L799`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L795-L799)). The reason is structural, not cosmetic: a dict or list returned from `parse_float` would be indistinguishable from a parsed table or array, and `key_value_rule` would mark its namespace FROZEN on the strength of an `isinstance` check ([`_parser.py#L455-L457`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L455-L457)). The guard stops the confusion at the door.

> **For the owner:** A custom `parse_float` that returns a dict or list raises a plain `ValueError`, not a `TOMLDecodeError` ([`_parser.py#L797-L798`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L797-L798)). Catch `ValueError` around `loads` whenever you pass `parse_float`, since that covers both this guard and `TOMLDecodeError`, which subclasses it. Note also that the callable runs on attacker-controlled text, so review it as parser code.

### What the exception would have carried

Every rejection in this chapter ends at the same constructor. `TOMLDecodeError` takes `msg`, `doc` and `pos`, derives the line from `doc.count("\n", 0, pos) + 1` and the column from the preceding newline, formats `"{msg} (at line L, column C)"` — or `"(at end of document)"` when `pos` is past the end — and then stores `msg`, `doc`, `pos`, `lineno` and `colno` on the instance ([`_parser.py#L132-L149`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L132-L149)). It subclasses `ValueError` ([`_parser.py#L91`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L91)). Constructing it with free-form arguments still works but warns, a deprecation kept for compatibility ([`_parser.py#L109-L130`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L109-L130)).

> **For the owner:** Branch on the exception type and on `msg`, `lineno`, `colno` and `pos`, never on `str(e)`. The README states plainly that error messages are informational only and should not be assumed to stay constant across Tomli versions ([`README.md#L103-L104`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/README.md#L103-L104)). Note that `doc` holds the entire document, so an error object logged verbatim will spill whatever secrets the config contains.

### Landing

Back in `key_value_rule`, the second value repeats chapter 5's checks with one different answer. `Flags.is_(('players',), FROZEN)` is still `False`. `get_or_create_nest(('players',))` walks into the list and returns `cont[-1]` again — and the trace shows what that dict now holds: `{'name': 'Lehtinen'}`, not `{}` ([`_parser.py#L304-L313`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L304-L313)). `'number'` is not in it, so the duplicate check passes; `26` is neither dict nor list, so no FROZEN flag is set; `nest['number'] = 26` ([`_parser.py#L453-L458`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L453-L458)). The first record is complete, and `key_value_rule` returns 42.

> **Leaves as:** `pos = 42`, `out.data.dict == {'players': [{'name': 'Lehtinen', 'number': 26}]}`, `header` still `('players',)`
