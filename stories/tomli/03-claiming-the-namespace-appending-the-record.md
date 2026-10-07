# Chapter 3 · Claiming the namespace, appending the record

> **Enters as:** `(10, ('players',))` inside `create_list_rule` — the key tuple read, the cursor on the first `]`, `out.data.dict` still `{}` and `out.flags` still empty

The name is parsed, but nothing has been promised yet. Before a single character of the document is turned into output, `create_list_rule` asks a question that has nothing to do with syntax: *is this namespace still open?*

```
if out.flags.is_(key, Flags.FROZEN):
    raise TOMLDecodeError(f"Cannot mutate immutable namespace {key}", src, pos)
```

([`_parser.py#L410-L411`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L410-L411)). The trace records the call as `Flags.is_(key=('players',), flag=0) → False` — `FROZEN` is the constant `0` ([`_parser.py#L239`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L239)). `is_` walks its internal nested dict of flags, finds `_flags` empty, and returns `False` from its last line ([`_parser.py#L275-L290`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L275-L290)). Nothing has frozen `('players',)`, because nothing has happened yet.

That is the *only* thing `create_list_rule` refuses up front, and it is worth putting next to its sibling. `create_dict_rule` — the rule for a single-bracket `[table]` — checks two flags, not one: `if out.flags.is_(key, Flags.EXPLICIT_NEST) or out.flags.is_(key, Flags.FROZEN): raise TOMLDecodeError(f"Cannot declare {key} twice", ...)` ([`_parser.py#L390-L391`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L390-L391)). That asymmetry is the whole reason this document is legal: `[[players]]` may appear again further down, `[players]` may not.

Having decided the namespace is open, the rule does something that looks destructive and is in fact the point:

```
# Free the namespace now that it points to another empty list item...
out.flags.unset_all(key)
# ...but this key precisely is still prohibited from table declaration
out.flags.set(key, Flags.EXPLICIT_NEST, recursive=False)
```

([`_parser.py#L412-L415`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L412-L415)). `unset_all` pops the key — and with it every flag recorded beneath it — out of the flag tree ([`_parser.py#L256-L262`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L256-L262)); on an empty tree it is a no-op, which is what the trace's `→ None` reflects. Then `set` creates the entry fresh and drops flag `1`, `EXPLICIT_NEST`, into its non-recursive `"flags"` set ([`_parser.py#L264-L273`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L264-L273), constant at [`_parser.py#L242`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L242)). Wipe the sub-namespace so the new record starts clean; re-claim the key itself so no `[players]` can ever reopen it.

Only now does anything get written. `out.data.append_nest_to_list(key)` ([`_parser.py#L417`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L417)) calls `get_or_create_nest(key[:-1])` — here `key[:-1]` is the empty tuple, so the loop body never runs and the document root itself comes back, the trace's `→ {}` ([`_parser.py#L298-L313`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L298-L313)). `'players'` is not in that root, so the `else` branch fires: `cont[last_key] = [{}]` ([`_parser.py#L315-L324`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L315-L324)). The output dict is now `{'players': [{}]}`, and that empty dict is the record the next two statements will fill.

The `if` branch is the interesting one. If `players` already existed and held something that was not a list, `append_nest_to_list` raises `KeyError("An object other than list found behind this key")` ([`_parser.py#L320-L321`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L320-L321)) — and `create_list_rule` catches it and re-raises as `TOMLDecodeError("Cannot overwrite a value", src, pos) from None` ([`_parser.py#L416-L419`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L416-L419)).

> **For the owner:** Structural clashes such as `a = true` followed by `[[a]]` surface as `TOMLDecodeError`, not as the internal `KeyError` the nested-dict helper raises. Catch `TOMLDecodeError` (or its base `ValueError`) around `loads` and you will catch these; the `from None` also suppresses the internal exception from the traceback, so error output stays clean.

Last, the closing brackets are verified rather than assumed: `if not src.startswith("]]", pos)` raises `"Expected ']]' at the end of an array declaration"`, otherwise the rule returns `pos + 2` ([`_parser.py#L421-L425`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L421-L425)). The trace's `→ (12, ('players',))` lands the cursor just past `]]`, and back in the loop that tuple is unpacked straight into `pos, header` ([`_parser.py#L211`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L211)) — `header` is now `('players',)` and will prefix every key until the next bracket statement.

What follows is the statement tail, and it is identical for every rule in the loop. Trailing whitespace is skipped (`skip_chars(…, 12, TOML_WS) → 12`, [`_parser.py#L214`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L214)). Then `skip_comment(src, 12)` ([`_parser.py#L219`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L219)) reads `src[12]`, sees `\n` rather than `#`, and returns 12 unchanged ([`_parser.py#L364-L373`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L364-L373)). Had there been a comment, `skip_until` would have run to the next newline — tolerating end-of-file, but raising `Found invalid character …` if any ASCII control character appeared inside it ([`_parser.py#L342-L361`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L342-L361), alphabet at [`_parser.py#L62`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L62)).

Then the loop insists on a clean break: the next character must be `\n`, or the document must end, or `TOMLDecodeError("Expected newline or end of document after a statement")` ([`_parser.py#L221-L230`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L221-L229)). It is `\n`; `pos += 1` makes it 13, and the loop's first step skips leading whitespace there, finding none.

> **For the owner:** There is no lenient mode. Trailing junk after a header, an unclosed bracket, or a stray character all abort the whole parse — `loads` either returns a complete document or raises. You never receive a partially parsed dict, which is the guarantee that makes it safe to use the result without checking whether parsing "mostly" worked.

The document's first record now exists as an empty dict inside a list inside the output, the header is set, and the cursor is poised on the `n` of `name`.

> **Leaves as:** `pos = 13`, `header = ('players',)`, `out.data.dict == {'players': [{}]}`, with `('players',)` flagged `EXPLICIT_NEST` and not `FROZEN`
