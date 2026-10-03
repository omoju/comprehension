# Chapter 6 · Flattening It Out

> **Enters as:** `attrs.asdict(inst=SomeClass(a_number=1, list_of_numbers=[1, 2, 3]), recurse=True, filter=None, value_serializer=None)`

The instance has no `__dict__`. Chapter 5 saw to that: its two values live in slots named `a_number` and `list_of_numbers`, and there is no mapping on the object to hand anyone. Yet the scenario asks for a dict.

## The wrapper that changes one default

The name imported from `attrs` is not the same function as `attr.asdict`. It is [a four-line wrapper](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_next_gen.py#L627-L640) that forwards the instance and then hard-codes `retain_collection_types=True`, leaving `dict_factory` at its `dict` default. The trace shows the hand-off exactly: the outer call carries four arguments, the inner call to [`attr.asdict`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L26-L33) carries six, with `dict_factory=<class 'dict'>` and `retain_collection_types=True` filled in.

That one flag is the only difference, and it is a behavioural one: the `attr`-namespace function [converts tuples, sets and frozensets to `list`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L101-L102) unless told otherwise, while the `attrs`-namespace one keeps them.

> **For the owner:** `attrs.asdict` and `attr.asdict` produce different output for the same instance whenever a field holds a tuple, set or frozenset. Pin down which namespace your serialization code imports from before changing any import.

## Finding out what the instance contains

The first thing [`asdict`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L78-L79) does is call [`fields(inst.__class__)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1924-L1972). It asks [`get_generic_base`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_compat.py#L98-L102) whether this is a specialized generic like `A[str]`; `SomeClass.__class__` is `type`, not `_GenericAlias`, so it gets `None` back (trace lines 141–142). `cls` is a real class, so [the instance-handling branch](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1950-L1956) is skipped, and [`getattr(cls, "__attrs_attrs__", None)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1958) returns the tuple `_ClassBuilder` stamped on in chapter 3.

So the answer to the missing `__dict__` is that the instance was never asked. The field names come from the class; the values come from `getattr`. A plain class would have fallen off the end into `NotAnAttrsClassError`, and a non-class, non-instance argument into `TypeError` — [both raised before any work is done](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1952-L1970).

A detail that matters for private fields: the loop reads values with [`getattr(inst, a.name)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L81) — the field *name*, not the alias chapter 2 computed. A field called `_x` appears in the output dict as `_x`, even though `__init__` takes it as `x`. The dict is not round-trippable through the constructor without renaming.

## Two values, two roads

`rv = dict_factory()` creates an empty dict, and the loop walks the two `Attribute`s in order.

**`a_number`.** `v = 1`. `filter` is `None`, so [the skip check](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L82-L83) doesn't fire; `value_serializer` is `None`, so [the hook](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L85-L86) doesn't run. `recurse` is `True`, so `value_type = type(v)` is computed once and checked against [`_ATOMIC_TYPES`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L9-L23) — a frozenset holding `NoneType`, `bool`, `int`, `float`, `str`, `complex`, `bytes`, `EllipsisType`, `type`, `range` and `property`. `int` is in it, so [`rv['a_number'] = 1`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L90-L91) and that is the whole story. The trace records no call at all for this field; the fast path is a set membership test.

**`list_of_numbers`.** `v = [1, 2, 3]`, `value_type = list`. Not atomic, so the next question is whether this is itself an *attrs* class: [`has(list)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L352-L377) looks for `__attrs_attrs__`, finds nothing, asks `get_generic_base(list)`, gets `None`, and returns `False` (trace lines 144–147). Had it been an attrs class, `asdict` would have recursed into itself with the same options.

It isn't, so [the collection branch](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L101-L121) takes it. `retain_collection_types` is `True`, so `cf = value_type` — `list`, the concrete class of this value, not a generic fallback. Each element is run through [`_asdict_anything`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L152-L227), which is `asdict`'s logic for values that aren't attrs instances: the same atomic / attrs-class / collection / dict / passthrough cascade, keyed on `type(val)`. All three elements are `int`, so all three take [the atomic path](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L163-L167) and come back unchanged — the trace's `_asdict_anything(val=1, …) → 1` and `×2 more`.

Then `rv['list_of_numbers'] = cf(items)` rebuilds the collection. [The `except TypeError` beside it](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L114-L121) is a targeted workaround: a namedtuple's `__new__` wants positional arguments, not an iterable, so if `cf(items)` fails *and* `cf` is a tuple subclass, attrs retries as `cf(*items)`. Any other collection type whose constructor accepts neither shape sees its `TypeError` propagate.

Two branches went unvisited. A `dict` value would have been rebuilt with [`dict_factory` over key/value pairs](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L122-L144), with keys passed `is_key=True` so a collection key collapses to a hashable tuple. And anything else — a `datetime`, a file handle, an arbitrary object — would have hit [the final `else`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_funcs.py#L145-L146) and been stored **as-is**.

> **For the owner:** `asdict` guarantees a dict, not a serializable one — unrecognized types are copied into the output untouched, and the rebuilt collections are shallow, so a nested mutable object is still shared with the original instance. Pass a `value_serializer` for every type your sink cannot encode, and do not treat the result as a snapshot you can mutate safely.

The loop ends, `rv` is returned through the wrapper unchanged, and the scenario's assertion holds: `{'a_number': 1, 'list_of_numbers': [1, 2, 3]}`.

> **Leaves as:** `{'a_number': 1, 'list_of_numbers': [1, 2, 3]}` — a fresh `dict` whose `'list_of_numbers'` is a new `list` object holding the same three `int`s
