# Chapter 5 · Where the value is allowed to land

> **Enters as:** `(30, ('name',), 'Lehtinen')` — unpacked into `key_value_rule`'s `pos`, `key`, `value`, with `header = ('players',)` and `out.data.dict == {'players': [{}]}`

The pair is parsed but homeless. `key_value_rule` now has to decide, in order: which dict the value belongs in, whether that dict is allowed to be written to, and whether the name is already taken. Only then does anything land.

### Computing the address

Two lines of arithmetic settle the destination:

```
key_parent, key_stem = key[:-1], key[-1]
abs_key_parent = header + key_parent
```

([`_parser.py#L432-L433`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L432-L433)). With `key = ('name',)`, `key_parent` is the empty tuple and `key_stem` is `'name'`, so `abs_key_parent` is just `('players',)` — the header the last `[[players]]` statement installed. This is the whole of the "current table" rule: a value is written under the header in force when its line was read, and nowhere else. A dotted key like `a.b.c = 1` would put `('a', 'b')` into `key_parent` and address the nested container instead, but the prefix is always the header.

Next comes a loop that, in this run, does not execute at all:

```
relative_path_cont_keys = (header + key[:i] for i in range(1, len(key)))
```

([`_parser.py#L435-L442`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L435-L442)). `len(key)` is 1, so `range(1, 1)` is empty and the generator yields nothing — which is why the trace shows no `Flags.add_pending` call between the return of `parse_key_value_pair` at line 62 and the `Flags.is_` at line 63. For a dotted key it would walk every intermediate container the key implies, refuse outright if one is already marked `EXPLICIT_NEST` (`Cannot redefine namespace {cont_key}`), and otherwise record a *pending* `EXPLICIT_NEST` on it via `add_pending` ([`_parser.py#L248-L249`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L248-L249)). Those pending marks are the subject of chapter 7; here it is enough that a single-part key creates none.

### Permission: is this namespace frozen?

```
if out.flags.is_(abs_key_parent, Flags.FROZEN):
    raise TOMLDecodeError(
        f"Cannot mutate immutable namespace {abs_key_parent}", src, pos
    )
```

([`_parser.py#L444-L447`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L444-L447)). The trace records `Flags.is_(key=('players',), flag=0) → False`. `Flags.is_` walks the key part by part through the nested flag tree, returning `True` early if any ancestor carries the flag in its `recursive_flags`, and finally checking the last part's own `flags` and `recursive_flags` ([`_parser.py#L275-L290`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L275-L290)). `('players',)` carries `EXPLICIT_NEST` from chapter 3 and nothing else, so the FROZEN query is `False` and the write may proceed.

This is also the answer to what FROZEN *is*. Nothing in table or array-of-tables syntax sets it; it is set a few lines below, and only for one kind of value — see the end of this chapter. Its effect is to close a namespace permanently: that check is what makes

```
a = { b = 1 }
a.b = 2
```

an error rather than an update ([`tests/data/invalid/inline-table/mutate.toml#L1-L2`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/invalid/inline-table/mutate.toml#L1-L2)).

### Finding the dict — and descending into the list

```
try:
    nest = out.data.get_or_create_nest(abs_key_parent)
except KeyError:
    raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None
```

([`_parser.py#L449-L452`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L449-L452)). The trace shows `NestedDict.get_or_create_nest(key=('players',), access_lists=True) → {}`.

That `{}` is not a new dict. `get_or_create_nest` starts at the root dict, and for each part of the key does three things ([`_parser.py#L298-L313`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L304-L313)): create an empty dict if the part is missing, step into it, and then — the line this whole chapter turns on —

```
if access_lists and isinstance(cont, list):
    cont = cont[-1]
```

([`_parser.py#L309-L310`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L309-L310)). `out.data.dict['players']` is a list, so the walk descends into its **last element** — the empty dict that `append_nest_to_list` pushed when the header was read. That single line is the entire implementation of "each `[[players]]` block starts a new record, and the lines beneath it fill that record in." Nothing else tracks which item is current; it is always `cont[-1]`.

If the walk met something that was neither dict nor list — say `a = 1` followed by `[a.b.c.d]` — it raises `KeyError("There is no nest behind this key")` ([`_parser.py#L311-L312`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L311-L312)), which the caller catches and converts into a `TOMLDecodeError`. That conversion matters: a structural clash in the document surfaces as a decode error with line and column, not as a bare `KeyError` escaping from internals.

Worth noticing in the other direction: missing intermediate keys are created silently ([`_parser.py#L305-L307`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L305-L307)). Implicit parent tables are legal TOML, so the parser manufactures them without comment.

### Permission, again: is the name taken?

```
if key_stem in nest:
    raise TOMLDecodeError("Cannot overwrite a value", src, pos)
```

([`_parser.py#L453-L454`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L453-L454)). `nest` is `{}`, so `'name'` is free. Had the same key already been assigned in this table, the document would be rejected — the parser never resolves a conflict by letting the later line win.

> **For the owner:** Duplicate keys in the same table are a hard error, not a last-writer-wins merge, and this holds for keys that look different but decode the same — `a = 1` and `"\u0061" = 1` collide, because the check is on the decoded `str` ([`tests/data/invalid/_external/toml-test/invalid/key/duplicate-keys-05.toml#L1-L2`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/invalid/_external/toml-test/invalid/key/duplicate-keys-05.toml#L1-L2)). If your config pipeline concatenates TOML fragments before parsing, expect the whole document to be rejected rather than quietly deduplicated.

### The write, and the branch not taken

```
if isinstance(value, (dict, list)):
    out.flags.set(header + key, Flags.FROZEN, recursive=True)
nest[key_stem] = value
return pos
```

([`_parser.py#L455-L459`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L455-L459)). `'Lehtinen'` is a `str`, so the `isinstance` test fails and no flag is set — which is why the trace shows no `Flags.set` call in this span. Had the value been an inline table or an array, this is where its namespace would be sealed: `recursive=True` puts FROZEN into `recursive_flags`, and `Flags.is_` returns `True` for that key and everything beneath it ([`_parser.py#L264-L273`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L264-L273), [`_parser.py#L282-L284`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L282-L284)). Inline tables are immutable in TOML, and this one line is the whole enforcement.

Then `nest['name'] = 'Lehtinen'`. Because `nest` *is* the dict sitting inside `out.data.dict['players'][0]`, the root dict now reads `{'players': [{'name': 'Lehtinen'}]}`. `key_value_rule` returns `30`.

> **For the owner:** Every rejection in this function — frozen namespace, non-dict in the path, duplicate key — raises before any mutation of that statement's value. But earlier statements have already been written into the dict, and `loads` discards it on the way out. There is no partial result to inspect: on `TOMLDecodeError` you get an exception and nothing else, so don't design a recovery path that expects half a document.

### Finishing the line

Back in the statement loop, the tail is identical for every rule ([`_parser.py#L218-L230`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L218-L230)). `skip_chars(src, 30, TOML_WS)` finds a newline immediately and returns 30. `skip_comment(src, 30)` sees no `#` and returns 30 unchanged ([`_parser.py#L364-L373`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L364-L373)). Then the loop insists on what the error message calls a clean ending:

```
if char != "\n":
    raise TOMLDecodeError(
        "Expected newline or end of document after a statement", src, pos
    )
pos += 1
```

`src[30]` is `'\n'`, so `pos` becomes 31 and the loop runs again from the top, where `skip_chars(src, 31, TOML_WS)` returns 31 — the cursor on the `n` of `number = 26`. This check is why `a = 1 b = 2` on one line is invalid: after the first pair, the next character is a space-then-`b`, not a newline.

> **Leaves as:** `pos = 31`, `out.data.dict == {'players': [{'name': 'Lehtinen'}]}`, `header` still `('players',)`
