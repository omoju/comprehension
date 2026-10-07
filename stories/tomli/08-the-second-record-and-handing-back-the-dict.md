# Chapter 8 · The second record, and handing back the dict

> **Enters as:** `pos = 55`, `header = ('players',)`, `out.data.dict == {'players': [{'name': 'Lehtinen', 'number': 26}, {}]}`

The header rule handed back position 55, and the statement that opened the second record still has to be closed the way every statement is closed. `skip_chars` at 55 finds no trailing whitespace and returns 55; `skip_comment` finds no `#` and returns 55; the character there is read and found to be `\n`, so `pos` becomes 56 ([`_parser.py#L218-L230`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L218-L230)). The loop turns over, skips leading whitespace — `skip_chars(pos=56) → 56` — and reads `n`, a bare-key character, which routes to `key_value_rule` ([`_parser.py#L201-L203`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L201-L203)).

From here the two remaining statements retrace roads already walked. `name = "Numminen"` goes through `parse_key` (bare-key scan 56 → 60, then whitespace to 61), the mandatory `=`, and `parse_value`, which sees `"` and calls `parse_one_line_basic_str` → `parse_basic_str(pos=64, multiline=False)`. That returns `(73, 'Numminen')` — the closing quote at 72, position 73 just past it, and the slice between the quotes as a plain `str` ([`_parser.py#L685-L687`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L685-L687)). `parse_key_value_pair` assembles the triple `(73, ('name',), 'Numminen')` ([`_parser.py#L462-L475`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L462-L475)).

### The same key, a different dict

Now the interesting part, and the reason the first record's `name` is not about to be overwritten. `key_value_rule` computes `abs_key_parent = header + key[:-1]`, which is `('players',)` again — the identical tuple used for the first record ([`_parser.py#L432-L433`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L432-L433)). It asks `Flags.is_(('players',), FROZEN)`, gets `False`, and walks:

```python
cont: Any = self.dict
for k in key:
    if k not in cont:
        cont[k] = {}
    cont = cont[k]
    if access_lists and isinstance(cont, list):
        cont = cont[-1]
```

([`_parser.py#L304-L313`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L298-L313)). `'players'` is present, it is a list, and `access_lists` is true, so the walk steps into `cont[-1]` — the empty dict appended by the header in the previous chapter. The trace records the return value plainly: `NestedDict.get_or_create_nest(key=('players',)) → {}`. The same key tuple, four lines of code later than last time, resolves to a different object, because the list grew underneath it.

`'name' not in nest`, so no duplicate-key error ([`_parser.py#L453-L454`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L453-L454)); the value is a `str`, not a dict or list, so no `FROZEN` mark is set ([`_parser.py#L455-L457`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L455-L457)); and `nest['name'] = 'Numminen'` writes straight into the second record ([`_parser.py#L458-L459`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L458-L459)). The rule returns 73.

### Twenty-seven

The statement tail runs again — `skip_chars(73) → 73`, `skip_comment(73) → 73`, `\n`, `pos = 74` — and `number = 27` follows the numeric road from chapter 6. The bare-key scan runs 74 → 80, whitespace to 81, `=` consumed, whitespace to 83, and `parse_value` falls past the string, boolean, array and inline-table tests into the regex section. `RE_DATETIME` and `RE_LOCALTIME` do not match; `RE_NUMBER` matches two characters, and the trace shows the handoff: `match_to_number(<re.Match span=(83, 85) '27'>, float) → 27`. With no `floatpart` group, `parse_float` is never called and `int(match.group(), 0)` produces a Python `int` ([`_re.py#L116-L119`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_re.py#L116-L119), [`_parser.py#L764-L766`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L764-L766)).

This time `get_or_create_nest(('players',))` returns `{'name': 'Numminen'}` — the same object as a moment ago, now holding one key. `'number'` is added beside it, and the rule returns 85.

### Falling off the end

The last statement tail: `skip_chars(85) → 85`, `skip_comment(85) → 85`, `src[85]` is the final `\n`, `pos` becomes 86. The loop turns over one more time, `skip_chars(86) → 86`, and then:

```python
try:
    char = src[pos]
except IndexError:
    break
```

([`_parser.py#L194-L197`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L194-L197)). The document is 86 characters long; there is no character at 86. The `IndexError` is the end-of-file signal, and it is caught in two places — here and again after the comment skip ([`_parser.py#L222-L225`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L222-L225)) — so a document ending in a newline, in trailing spaces, in a comment with no newline, or in nothing at all, all terminate cleanly rather than erroring.

Then one line:

```python
return out.data.dict
```

([`_parser.py#L232`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L232)). Not a copy, not a wrapper — the very dict that `NestedDict.__init__` created at the start of the call ([`_parser.py#L293-L296`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L293-L296)) and that every `nest[key_stem] = value` has been filling in place. The `Output`, the `Flags`, the flag tree, the pending set, the 86-character `src` copy: all of it is local to the frame and goes away when the frame does ([`_parser.py#L175-L178`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L175-L178)). What crosses back over the boundary is:

```python
{'players': [{'name': 'Lehtinen', 'number': 26}, {'name': 'Numminen', 'number': 27}]}
```

> **For the owner:** The returned value is a plain `dict` of builtin and stdlib types only — `str`, `int`, `float` (or whatever `parse_float` returned), `bool`, `datetime`/`date`/`time`, `list`, `dict` ([README type table](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/README.md#L185-L199)). It is the parser's own object handed over whole rather than copied ([`_parser.py#L232`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L232)), and each call builds a fresh `Output` ([`_parser.py#L176`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L176)), so the result is yours to mutate and two concurrent calls cannot share state.

> **For the owner:** A header with no key/value pairs under it is valid and yields an empty dict, not an error — `[[players]]` alone parses to `{"players": [{}]}` ([`table/array-empty.toml`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/valid/_external/toml-test/valid/table/array-empty.toml#L1), [`array-empty.json`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/valid/_external/toml-test/valid/table/array-empty.json#L1-L3)). Validate required fields after parsing; a successful `loads` guarantees syntax, not shape.

> **For the owner:** Parsing is single-pass over one in-memory string, and the only size bounds in the module are `MAX_INLINE_NESTING = 400` ([`_parser.py#L43`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L43)) and `MAX_KEY_PARTS` ([`_parser.py#L50`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L50)); document length and literal length are uncapped, and `loads` additionally holds a newline-normalized copy of the input ([`_parser.py#L169-L174`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L169-L174)). Impose your own size limit before parsing untrusted input.

> **Leaves as:** `{'players': [{'name': 'Lehtinen', 'number': 26}, {'name': 'Numminen', 'number': 27}]}` — a plain dict, returned to the caller
