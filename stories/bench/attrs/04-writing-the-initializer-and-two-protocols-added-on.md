# Chapter 4 · Writing the Initializer, and Two Protocols Added Only If Vacant

> **Enters as:** `_make_init_script(cls, attrs=(Attribute(name='a_number', default=42, …), Attribute(name='list_of_numbers', default=Factory(list), …)), pre_init=False, pre_init_has_args=False, post_init=False, frozen=False, slots=True, cache_hash=False, base_attr_map={}, is_exc=False, cls_on_setattr=None, attrs_init=False)`

`props.added_init` is `True`, so [`attrs.wrap` calls `builder.add_init()`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1595-L1601), and the two `Attribute`s go off to be turned into source for the one method a caller actually types. The alternative branch — `init=False` — would have routed the identical script to `__attrs_init__` instead, leaving the user's own `__init__` untouched; it also rejects `cache_hash=True` there, since there'd be nothing to initialize the cache.

Notice what `add_init` passes as `cls_on_setattr`: `self._on_setattr`, which chapter 3 set to `None`. So the first thing `_make_init_script` computes, [`has_cls_on_setattr`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2044-L2046), is `False`. That single `False` propagates all the way down and decides what the assignment statements will look like.

`_make_init_script` then does its own filtering: [any field that is both `init=False` and has no default is skipped entirely](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2053-L2060) — there'd be nothing to set it from. Both of ours survive, and both land in `attr_dict`, a `{name: Attribute}` map that the generated code will consult at runtime. Alongside it, [`needs_cached_setattr = cache_hash or frozen`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2052) is `False`, and no field carries an `on_setattr`, so it stays `False`. The script will not open with `_setattr = _cached_setattr_get(self)`.

## Four lines of body

Inside [`_attrs_to_init_script`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2187-L2448), the first decision is how to write a value onto an instance. [`_determine_setters(frozen=False, slots=True, base_attr_map={})`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2140-L2184) returns, as the trace records, `((), <function _assign>, <function _assign_with_converter>)` — no preamble lines and the plainest strategy there is. A frozen slotted class would get `_setattr` (going through a cached `object.__setattr__`); a frozen dict class would get direct `_inst_dict['x'] = …` writes. Ours gets ordinary attribute assignment.

Then the loop over fields. For each one, [`arg_name = a.alias`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2236-L2242) — this is where chapter 2's quiet `name.lstrip("_")` becomes the public contract. The parameter in the signature is the alias; the attribute written on `self` is the name.

`a_number` has a default that isn't a `Factory`, so it takes [the simple branch](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2296-L2314): the parameter becomes `a_number=attr_dict['a_number'].default` and the body gets one call to `_assign`, which the trace shows returning `'self.a_number = a_number'`. Because `has_on_setattr` is `False`, [`_assign` takes its fast path](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2116-L2124) and emits a bare assignment instead of relegating to `_setattr`.

The default is referenced *indirectly*, through `attr_dict`, so the `Attribute` object remains the single source of truth rather than having `42` baked into the string. Python evaluates default expressions once, when the `def` is executed — which is why a mutable default would be shared across every instance, and why `Factory` exists at all.

`list_of_numbers` takes [the factory branch](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2316-L2359). Its parameter becomes `list_of_numbers=NOTHING` — a sentinel, not a list — and the body gets three more lines and two more `_assign` calls (the trace's `_assign ×2 more`):

```
if list_of_numbers is not NOTHING:
    self.list_of_numbers = list_of_numbers
else:
    self.list_of_numbers = __attr_factory_list_of_numbers()
```

The factory is injected into the globals under the mangled name from [`_INIT_FACTORY_PAT = "__attr_factory_%s"`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L40), and the trace confirms the payload: `{'__attr_factory_list_of_numbers': <class 'list'>}`. That `else` branch is the guarantee: each construction calls `list()` again, so no two instances share a list.

Two more blocks would have been appended if the class had asked for them. Validators are collected into `attrs_to_validate` and emitted *after* every assignment, inside [`if _config._run_validators is True:`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2386-L2394) — so a validator always sees a fully populated instance, and the whole set can be switched off globally at runtime. A `__attrs_post_init__` would have been called at the very end. `SomeClass` has neither.

The function returns the script, the globs `{'__attr_factory_list_of_numbers': list}`, and `annotations = {'a_number': int, 'list_of_numbers': list[int], 'return': None}`, built from [`a.type` for each `init=True` field](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2379-L2384) — keyed, again, by alias.

## The namespace the initializer will live in

Back in `_make_init_script`, two updates widen those globs considerably. First, [if the defining module is importable, its entire `__dict__` is merged in](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2085-L2087) — the trace's return shows `'Factory'`, `'SomeClass'`, `'_SRC'`, `'__builtins__'` and the rest of the scenario's module sitting next to the factory. The stated reason is one line of comment: *"This makes `typing.get_type_hints(CLS.__init__)` resolve string types."* Then [`NOTHING` and `attr_dict` are added](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2089), which the script needs for its sentinel check and its default lookup.

> **For the owner:** The generated `__init__` executes with a copy of your module's namespace as its globals, and the module's names are merged in *after* the ones attrs injected, so a module-level name shaped like `__attr_factory_<field>`, `__attr_validator_<field>` or `__attr_converter_<field>` silently replaces the callable attrs meant to use. Do not define module-level names in that form.

`add_init` queues the snippet and a `_attach_init` hook that will later set `init.__annotations__ = annotations` and stamp the function onto the class dict. Nothing is compiled yet.

## Added only if vacant

Two protocol attributes follow, each gated the same way. [`PY_3_13_PLUS and not _has_own_attribute(cls, "__replace__")`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1603-L1604) — the interpreter is new enough, and [`_has_own_attribute`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L313-L317), which checks `cls.__dict__` and nothing else, returns `False`. So [`add_replace`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1110-L1116) defines a three-line proxy and hands it to `_add_method_dunders_unsafe`, which mutates it in place — the trace shows the same object address, `0x10e173ba0`, going in anonymous and coming out as `<function SomeClass.__replace__>`.

> **For the owner:** `copy.replace(instance, …)` on these classes is not a field-by-field copy; [`evolve`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L634-L644) re-runs `__init__` with each field's *alias* as a keyword, so all converters and validators fire again and any `init=False` field is skipped rather than carried over. Check that your `init=False` fields can be recomputed before you let callers use `copy.replace`.

The same `_has_own_attribute` check clears `__match_args__`, and [`add_match_args`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1118-L1123) writes `('a_number', 'list_of_numbers')` — every field that is `init=True` and not keyword-only.

> **For the owner:** `__match_args__` is built from `field.name`, while `__init__` parameters come from `field.alias`. For a private field `_x` the constructor takes `x` but a positional `case C(…)` pattern binds through `_x`. Confirm this asymmetry is acceptable before relying on pattern matching over classes with underscore-prefixed fields.

> **Leaves as:** a third queued snippet — script `def __init__(self, a_number=attr_dict['a_number'].default, list_of_numbers=NOTHING): …` with globs containing `__attr_factory_list_of_numbers`, `NOTHING`, `attr_dict` and the defining module's namespace, and annotations `{'a_number': int, 'list_of_numbers': list[int], 'return': None}` — plus `cls_dict['__replace__'] = <function SomeClass.__replace__>` and `cls_dict['__match_args__'] = ('a_number', 'list_of_numbers')`
