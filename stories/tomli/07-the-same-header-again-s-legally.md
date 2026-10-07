# Chapter 7 · The same header again, legally

> **Enters as:** `pos = 42`, `header = ('players',)`, `out.data.dict == {'players': [{'name': 'Lehtinen', 'number': 26}]}` — the cursor on the newline that ends `number = 26`

The first record is finished, but the statement is not. Back in the loop, the same three steps that close every statement run again: `skip_chars` finds no trailing whitespace and returns 42, `skip_comment` finds no `#` and returns 42, and then the character at 42 is read and tested ([`_parser.py#L218-L230`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L218-L230)). It is `\n`, so `pos` becomes 43 and the loop turns over. Anything else there — a stray word, a second key — would have raised `TOMLDecodeError("Expected newline or end of document after a statement", src, pos)` ([`_parser.py#L226-L230`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L226-L230)).

Position 43 is the blank line separating the two records. The loop's first step skips leading whitespace (trace: `skip_chars(pos=43) → 43`), reads `\n`, and takes the cheapest branch in the whole parser:

```python
if char == "\n":
    pos += 1
    continue
```

([`_parser.py#L198-L200`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L198-L200)). No rule, no comment scan, no end-of-statement check. `pos` is 44, and the next `skip_chars` leaves it there.

### Two brackets, and a flush before the rule

At 44 the character is `[`, which means a header — but which kind is decided by the character after it, read defensively:

```python
try:
    second_char: str | None = src[pos + 1]
except IndexError:
    second_char = None
out.flags.finalize_pending()
if second_char == "[":
    pos, header = create_list_rule(src, pos, out)
else:
    pos, header = create_dict_rule(src, pos, out)
```

([`_parser.py#L204-L213`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L204-L213)). A document ending in a lone `[` would set `second_char = None` and fall into `create_dict_rule`, which fails with a decode error rather than an `IndexError`. Here `src[45]` is `[`, so the array-of-tables rule is chosen.

Note what happens *between* the two: `finalize_pending()`. The trace shows the call and a `None` return — it does nothing in this run, because nothing is pending. But its placement is the whole mechanism, so it is worth saying what it would have done.

`Flags` keeps two kinds of marks. `set` writes a flag immediately; `add_pending` only drops `(key, flag)` into a set to be applied later ([`_parser.py#L248-L254`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L248-L254)). The only caller of `add_pending` is `key_value_rule`, which records an `EXPLICIT_NEST` mark for every intermediate container a dotted key creates, with the comment that those containers "can't be opened with the table syntax or dotted key/value syntax in following table sections" ([`_parser.py#L435-L442`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L435-L442)). Committing those marks straight away would be too strict: the same rule checks `is_(cont_key, EXPLICIT_NEST)` two lines earlier and raises `Cannot redefine namespace` if set, so `b.c = 1` followed by `b.d = 2` inside one table would reject itself on the shared `b`. That pattern is a valid fixture ([`key/dotted-04.toml#L4-L5`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/valid/_external/toml-test/valid/key/dotted-04.toml#L4-L5)). Deferring the marks until the next `[`-headed statement keeps the current table writable and still slams the door afterwards: `[t1]` / `t2.t3.v = 0` / `[t1.t2]` is invalid ([`table/redefine-1.toml#L1-L3`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/invalid/table/redefine-1.toml#L1-L3)).

### The one check this rule makes

`create_list_rule` skips the two brackets (44 → 46), trims whitespace, and parses the key exactly as in chapter 2: the trace shows `parse_key(pos=46) → (53, ('players',))`. Then comes the gate:

```python
if out.flags.is_(key, Flags.FROZEN):
    raise TOMLDecodeError(f"Cannot mutate immutable namespace {key}", src, pos)
```

([`_parser.py#L410-L411`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L410-L411)). That is the *only* flag it consults — the trace confirms a single `Flags.is_(('players',), 0) → False`. Its sibling `create_dict_rule` checks two:

```python
if out.flags.is_(key, Flags.EXPLICIT_NEST) or out.flags.is_(key, Flags.FROZEN):
    raise TOMLDecodeError(f"Cannot declare {key} twice", src, pos)
```

([`_parser.py#L390-L391`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L390-L391)). That asymmetry is the entire answer to why this header may appear twice: a `[table]` is refused if the name is already an explicit nest, an `[[array]]` is not.

> **For the owner:** A `[table]` header is guaranteed to be unique within a document, but a `[[table]]` header is not, and the parser treats a repeat as an append rather than an error ([`_parser.py#L390-L391`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L390-L391), [`_parser.py#L410-L417`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L410-L417)). Mixing the two forms on one name is rejected in both orders ([`table/duplicate-key-07.toml#L1-L2`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/invalid/_external/toml-test/invalid/table/duplicate-key-07.toml#L1-L2)). If your schema assumes a key appears once, validate the list length yourself after parsing.

### Freeing the namespace, then re-claiming the name

Two lines, with the reasoning written beside them:

```python
# Free the namespace now that it points to another empty list item...
out.flags.unset_all(key)
# ...but this key precisely is still prohibited from table declaration
out.flags.set(key, Flags.EXPLICIT_NEST, recursive=False)
```

([`_parser.py#L412-L415`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L412-L415)). `unset_all` walks to the parent container and pops the key, taking its whole `"nested"` subtree of flags with it ([`_parser.py#L256-L262`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L256-L262)). Everything the first record marked beneath `('players',)` is forgotten, which is what lets the second record use the same dotted-key prefixes again. `set` then immediately re-writes the single `EXPLICIT_NEST` mark on `('players',)` itself, so a later `[players]` still fails ([`_parser.py#L264-L273`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L264-L273)).

Nothing about duplicate *keys* is lost in that wipe. Duplicate detection inside a record is done against the dict itself — `if key_stem in nest` ([`_parser.py#L453-L454`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L453-L454)) — and the second record's dict is brand new.

### The new record

```python
def append_nest_to_list(self, key: Key) -> None:
    cont = self.get_or_create_nest(key[:-1])
    last_key = key[-1]
    if last_key in cont:
        list_ = cont[last_key]
        if not isinstance(list_, list):
            raise KeyError("An object other than list found behind this key")
        list_.append({})
    else:
        cont[last_key] = [{}]
```

([`_parser.py#L315-L324`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L315-L324)). `key[:-1]` is empty, so `get_or_create_nest(())` returns the document root — and the trace shows it is no longer empty: `{'players': [{'name': 'Lehtinen', 'number': 26}]}`. `'players'` is present and is a list, so a fresh `{}` is appended. That empty dict is now `list[-1]`, which is exactly what `get_or_create_nest` will descend into for every key/value statement that follows.

The `KeyError` branch is for a name already holding something that is not a list — `a = true` followed by `[[a]]` ([`array-of-tables/overwrite-bool-with-aot.toml#L1`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/tests/data/invalid/array-of-tables/overwrite-bool-with-aot.toml#L1)). The caller converts it: `except KeyError: raise TOMLDecodeError("Cannot overwrite a value", src, pos) from None` ([`_parser.py#L416-L419`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L416-L419)).

> **For the owner:** Every internal `KeyError` raised by the nested-dict layer is caught and re-raised as `TOMLDecodeError` at each of its three call sites ([`_parser.py#L393-L396`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L393-L396), [`_parser.py#L416-L419`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L416-L419), [`_parser.py#L449-L452`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L449-L452)). Treat `TOMLDecodeError`, `TypeError` and `RecursionError` as the complete failure surface for a malformed document, and report anything else as a bug.

Finally the rule insists on the closing brackets — `src.startswith("]]", 53)` holds, otherwise `Expected ']]' at the end of an array declaration` ([`_parser.py#L421-L424`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L421-L424)) — and returns `(55, ('players',))`. Back in the loop, that tuple is unpacked into `pos` and `header` ([`_parser.py#L211`](https://github.com/hukkin/tomli/blob/18d8d59db6d632ebbcfe63f1f7636145d652da21/src/tomli/_parser.py#L211)). The header string is identical to the one bound thirty characters earlier; the dict it now points at is not.

> **Leaves as:** `pos = 55`, `header = ('players',)`, `out.data.dict == {'players': [{'name': 'Lehtinen', 'number': 26}, {}]}`, with `EXPLICIT_NEST` set on `('players',)` and nothing pending
