# Chapter 4 · A key, an equals sign, and a quoted string

> **Enters as:** `src`, `pos = 13`, `header = ('players',)`, `parse_float = float` — the cursor resting on the `n` of `name = "Lehtinen"`

The statement loop looked at `src[13]`, found `'n'` in `KEY_INITIAL_CHARS`, and routed the line to `key_value_rule` ([`_parser.py#L201-L203`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L201-L203)). That rule's very first act is to delegate: `pos, key, value = parse_key_value_pair(src, pos, parse_float, nest_lvl=0)` ([`_parser.py#L428-L431`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L428-L431)). Note the `nest_lvl=0`. Nothing in the trace will change it, because it is incremented only when the parser descends into an array or an inline table — but it is the seed of a safety bound, and it travels with the data from here on.

### The key, again

`parse_key_value_pair` calls the same `parse_key` that read the table header one chapter ago ([`_parser.py#L465`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L465)). There is only one key grammar in TOML, and only one implementation of it; a bare word, a `'literal'` part, a `"basic"` part and a dotted chain all behave identically whether they name a table or a value.

`parse_key_part(src, 13)` sees `'n'` in `BARE_KEY_CHARS`, runs `skip_chars` across the bare alphabet to 17, and slices out `'name'` — the trace's `→ (17, 'name')` ([`_parser.py#L500-L508`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L500-L508)). Back in `parse_key`, the part is wrapped into the one-element tuple `('name',)`, whitespace is skipped (17 → 18, swallowing the space before `=`), and the loop checks whether the next character is a dot ([`_parser.py#L478-L498`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L478-L488)). It is `'='`, so the loop returns immediately: `(18, ('name',))`. Had it been a dot, the loop would have appended another part and then enforced `MAX_KEY_PARTS`, raising `RecursionError` past `sys.getrecursionlimit()` parts ([`_parser.py#L489-L497`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L489-L497)) — a bound added because `Flags.is_` costs time proportional to key length.

The cursor is parked on the `=`, and `parse_key_value_pair` insists on finding it there:

```
if char != "=":
    raise TOMLDecodeError("Expected '=' after a key in a key/value pair", src, pos)
```

([`_parser.py#L466-L471`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L466-L471)). The read is wrapped in `try/except IndexError` so that a document ending right after a key — `fs.fw`, one of the invalid fixtures — produces that same decode error rather than an `IndexError`. Then `pos += 1` and `skip_chars` over the space: 19 → 20 ([`_parser.py#L472-L473`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L472-L473)).

### Choosing what kind of value this is

`parse_value(src, 20, float, 0)` ([`_parser.py#L703-L705`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L703-L705)) begins with the guard that `nest_lvl` was carried here for:

```
if nest_lvl > MAX_INLINE_NESTING:
    raise RecursionError(
        "TOML inline arrays/tables are nested more than the allowed"
        f" {MAX_INLINE_NESTING} levels"
    )
```

([`_parser.py#L706-L712`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L706-L712)). `MAX_INLINE_NESTING` is 400, and the comment above it explains the choice plainly: inline tables and arrays are parsed by recursion, pure Python would raise `RecursionError` on its own, but a mypyc-compiled binary would crash the process unrecoverably instead ([`_parser.py#L32-L43`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L32-L43)). At `nest_lvl = 0` the check costs one comparison and passes.

> **For the owner:** Pathologically nested input raises `RecursionError`, not `TOMLDecodeError`, and `RecursionError` does not inherit from `ValueError`. Catch both when parsing untrusted documents — the project's own fuzzer does exactly that ([`fuzzer/fuzz.py#L26-L27`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/fuzzer/fuzz.py#L26-L27)). Treat the 400-level cap as a crash guard for the binary wheels, not as a general input-size limit; nothing here bounds document length.

Then comes a chain of `if`s whose order is deliberate, flagged by a comment reading *"IMPORTANT: order conditions based on speed of checking and likelihood"* ([`_parser.py#L719`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L719)). The character at 20 is `"`, so the very first branch fires. It asks whether three quotes start here — `src[20:23]` is `"Le`, so no — and falls through to the single-line form ([`_parser.py#L721-L725`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L721-L725)). Everything below is skipped untouched: literals, `true`/`false`, `[`, `{`, the datetime and number regexes, and finally the `inf`/`nan` prefixes before the catch-all `raise TOMLDecodeError("Invalid value", src, pos)` ([`_parser.py#L776`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L776)). That last line is where `val=.` and a key with nothing after the `=` both end up — in the second case `char` is `None`, every test fails, and the error reports *at end of document*.

### Eight characters, checked one at a time

`parse_one_line_basic_str` does one thing: step over the opening quote and hand off with `multiline=False` ([`_parser.py#L516-L518`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L516-L518)). The trace shows `parse_basic_str(src, pos=21, multiline=False)`.

Inside, the `multiline` flag picks two things: the set of characters that are illegal, and the escape handler ([`_parser.py#L671-L677`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L671-L677)). For a one-line string the alphabet is `ILLEGAL_BASIC_STR_CHARS` — every ASCII control character plus DEL, minus tab ([`_parser.py#L52-L56`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L52-L56)). A raw newline is in that set, which is why `a = "\n"` written literally across two lines is rejected.

Then the scan: remember `start_pos = 21`, walk forward, and dispatch on each character ([`_parser.py#L678-L700`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L680-L700)). `L`, `e`, `h`, `t`, `i`, `n`, `e`, `n` are none of `"`, `\`, or an illegal character, so each one just advances `pos`. No slicing, no concatenation — the loop is deliberately doing nothing until it has a reason to. At 29 it meets `"`, and since this is not a multiline string it returns on the spot: `pos + 1, result + src[start_pos:pos]` → `(30, 'Lehtinen')`, one slice for the whole string.

The three branches not taken are where the guarantees live. On `IndexError` — running off the end of the document — it raises `TOMLDecodeError("Unterminated string")` ([`_parser.py#L681-L684`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L681-L684)). On a control character it raises `Illegal character {char!r}` ([`_parser.py#L698-L699`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L698-L699)). On a backslash it flushes the pending slice, calls the escape parser, appends the replacement and resets `start_pos` ([`_parser.py#L692-L697`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L692-L697)). That escape parser accepts only the eight entries in `BASIC_STR_ESCAPE_REPLACEMENTS` plus `\x`, `\u` and `\U` ([`_parser.py#L72-L83`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L72-L83), [`_parser.py#L602-L611`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L602-L611)); anything else is `Unescaped '\' in a string`. Hex escapes must be the right length and real hex digits, and the resulting codepoint must be a Unicode scalar value — surrogates are rejected with `Escaped character is not a Unicode scalar value` ([`_parser.py#L618-L628`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L618-L628), [`_parser.py#L779-L780`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L779-L780)).

> **For the owner:** Raw control characters are rejected, but *escaped* ones are not — `"\u0000"` and `"\x7f"` parse successfully into real NUL and DEL characters in the returned `str`. Do not assume strings coming out of `loads` are safe to splice into log lines, filenames or terminals; sanitise them at the point of use.

The value climbs back out unchanged through `parse_one_line_basic_str` and `parse_value`, and `parse_key_value_pair` assembles the three things the caller asked for ([`_parser.py#L474-L475`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L474-L475)): the new cursor, the key tuple, and a plain Python `str` — exactly the mapping the README's type table promises for a TOML String.

Nothing has been written to the output dict yet. The pair is still in flight, and the question of *which* dict may receive it is the next chapter's.

> **Leaves as:** `(30, ('name',), 'Lehtinen')` — returned from `parse_key_value_pair` into `key_value_rule`'s `pos, key, value`
