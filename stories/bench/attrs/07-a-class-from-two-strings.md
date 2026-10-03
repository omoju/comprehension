# Chapter 7 · A Class From Two Strings

> **Enters as:** `make_class(name='C', attrs=['a', 'b'], bases=(<class 'object'>,), class_body=None)`

Everything so far began with a class body someone typed. This time the input is a string and a list of two more strings, and the scenario expects a working class out the other end. The same machinery is about to run — but it enters through a different door, and the door has different defaults nailed to it.

## Normalizing the name, then trusting it

The first thing [`make_class`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3261-L3262) does to `'C'` is run it through [`unicodedata.normalize("NFKC", name)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3308-L3309). That is the same normalization the Python parser applies to identifiers, so a name like `"ℂ"` arrives as the class `C` — matching what you'd get from writing `class ℂ:` by hand. For the plain ASCII `'C'` in this run, nothing changes.

That is the *only* thing done to the name. The docstring says so [in a warning block](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3276-L3281): it is the caller's duty to ensure the class name and attribute names are valid identifiers, and `make_class` will not validate them. The reason is visible from chapter 5: the field names are pasted verbatim into source strings that get `compile()`d. A name that isn't an identifier doesn't produce a polite error here — it produces a `SyntaxError` out of the generated-code compiler, pointing at a synthetic filename.

> **For the owner:** `make_class` accepts any strings as class and field names and interpolates them into generated source before compiling it. Validate any name that originates outside your own code — from config, a schema, or user input — before passing it to `make_class`.

## Two strings become two field definitions

`attrs` is a `list`, so [the list branch](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3311-L3317) builds `cls_dict = {a: attrib() for a in attrs}`, preserving order. A `dict` input would have been used as-is; anything else raises `TypeError: attrs argument must be a dict or a list.` before a class exists.

So `'a'` and `'b'` each get a call to [`attrib()`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L104-L120) with every parameter at its default. Inside, [`_determine_attrib_eq_order(None, None, None, True)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1284-L1324) takes the `eq is None` path and returns the default `True` with no key function, then [order mirrors eq](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1315-L1316) — the trace's `→ (True, None, True, None)`. `factory` is `None`, so [the default/factory exclusivity check](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L173-L182) is skipped and `default` stays `NOTHING`: both fields are mandatory.

Each call ends in [a `_CountingAttr`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L197-L214), whose constructor [bumps a class-level counter](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L2828-L2829) — `counter=8` for `a`, `counter=9` for `b` in this process, following the `6` and `7` that `SomeClass`'s fields took in chapter 2. That counter exists so that fields declared in a class body can be sorted back into definition order; here the dict already preserves it.

The dict now holds exactly what `@define` found by scanning a class body. The two strings have become field definitions.

## A class with nothing in it

Before building, [three names are *popped* out](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3319-L3321) of `cls_dict`: `__attrs_pre_init__`, `__attrs_post_init__`, and `__init__`. They, plus any `class_body` you passed, go into a separate `body` dict and are [installed as real class members](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3323-L3331). This is the seam that lets you hand `make_class` your hooks in the same mapping as your fields without attrs mistaking a function for a field. Here all three are absent.

[`types.new_class(name, bases, {}, lambda ns: ns.update(body))`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3333) produces a bare `C` subclassing `object` with an empty body — the blank canvas that chapter 8 will paint on. Then [`sys._getframe(1)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3335-L3342) reaches up one stack frame to the caller and copies its `__name__` into `type_.__module__`, so that `pickle` can find the class again by module path. The whole thing sits inside `contextlib.suppress(AttributeError, ValueError)`: on interpreters without frame introspection the module stays wrong rather than the call failing.

## The defaults you inherit by using this door

[`_determine_attrs_eq_order(cmp=None, eq=None, order=None, default_eq=True)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3344-L3354) runs here, with `default_eq=True`, and returns `(True, True)` — equality *and* ordering, written back into `attributes_arguments`. Compare chapter 1, where `define` passed `default_eq=None` and got `(None, False)`.

Then [`_attrs(these=cls_dict, **attributes_arguments)(type_)`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3356). `_attrs` is the internal alias for `attr.s`, **not** `attrs.define` — the docstring [calls this out explicitly](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3267-L3274). Everything the caller didn't name falls to [`attrs`'s own defaults](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1353-L1379), and the trace records the result: `slots=False`, `auto_detect=False`, `auto_exc=False`, `collect_by_mro=False`, `on_setattr=None`, `force_kw_only=True`. Every one of those is the opposite of what `@define` chose [in chapter 1](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_next_gen.py#L23-L47).

The consequence that bites hardest is `on_setattr=None`: `define` would have installed the convert-and-validate pipe, but `attr.s` installs nothing, so a `make_class` class never re-runs converters or validators when you assign to an attribute after construction.

> **For the owner:** classes built by `make_class` are dict classes with ordering enabled and no `on_setattr` hooks, because it wraps `attr.s` rather than `define`. If you need converters and validators to run on assignment, pass `on_setattr=setters.pipe(setters.convert, setters.validate)` to `make_class` yourself.

Inside `attrs`, [`_determine_attrs_eq_order`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1469) runs a second time — now with the explicit `eq=True, order=True` — and confirms `(True, True)`. `maybe_cls` is `None` because `make_class` called the decorator in two steps, so [`attrs` returns the `wrap` closure](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L1611-L1616) instead of building anything.

One last thing waits for after the build: [`cls.__annotations__`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3357-L3360) is set from the fields' `type` values only once the class is finished — because setting annotations earlier would have made `_transform_attrs` read them as auto-attribs declarations. Neither field here has a type, so that dict will come out empty.

> **Leaves as:** `<function attrs.<locals>.wrap>`, closed over `these={'a': _CountingAttr(counter=8, _default=NOTHING, eq=True, order=True, alias=None), 'b': _CountingAttr(counter=9, …)}`, `slots=False`, `auto_detect=False`, `collect_by_mro=False`, `eq=True`, `order=True`, `force_kw_only=True` — about to be called with the bare `C` built by `types.new_class`
