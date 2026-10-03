"""Chapter 7: make_class turns two strings into field definitions and an attr.s wrap closure.

Run from the repository root with PYTHONPATH=src.
"""

import inspect
import unicodedata

from attr._make import (
    NOTHING,
    _CountingAttr,
    _determine_attrib_eq_order,
    _determine_attrs_eq_order,
    attrib,
    attrs as attrs_decorator,
    make_class,
)
from attrs import fields


# --- trace 154-160: each name becomes a default attrib() -> _CountingAttr ---
a_ca = attrib()
b_ca = attrib()

assert isinstance(a_ca, _CountingAttr)
assert a_ca._default is NOTHING          # mandatory field
assert a_ca.eq is True and a_ca.order is True
assert a_ca.eq_key is None and a_ca.order_key is None
assert a_ca.alias is None                # no explicit alias yet
assert a_ca.kw_only is None
assert a_ca.metadata == {}
# the counter advances by exactly one per attrib(), as 8 -> 9 in the trace
assert b_ca.counter == a_ca.counter + 1

# trace 155-156: the eq/order resolution inside attrib()
assert _determine_attrib_eq_order(None, None, None, True) == (True, None, True, None)

# --- trace 161-162: make_class resolves eq/order with default_eq=True ---
assert _determine_attrs_eq_order(None, None, None, True) == (True, True)
# contrast with chapter 1, where define passed default_eq=None:
assert _determine_attrs_eq_order(None, None, False, None) == (None, False)

# --- trace 163-166: attrs(maybe_cls=None, ...) returns the wrap closure ---
w = attrs_decorator(
    maybe_cls=None,
    these={"a": attrib(), "b": attrib()},
    eq=True,
    order=True,
)
assert callable(w)
assert w.__qualname__ == "attrs.<locals>.wrap"

# make_class rides on attr.s's defaults, not define's (trace line 163 arguments)
sig = inspect.signature(attrs_decorator)
assert sig.parameters["slots"].default is False
assert sig.parameters["auto_detect"].default is False
assert sig.parameters["auto_exc"].default is False
assert sig.parameters["collect_by_mro"].default is False
assert sig.parameters["on_setattr"].default is None
assert sig.parameters["force_kw_only"].default is True

# --- trace 153: the scenario's own call, end to end ---
C = make_class("C", ["a", "b"])
assert [f.name for f in fields(C)] == ["a", "b"]
assert [f.alias for f in fields(C)] == ["a", "b"]
assert all(f.default is NOTHING for f in fields(C))
# annotations are attached only after the build, and both types are None
assert C.__annotations__ == {}
# __module__ was patched from the caller's frame so pickle can find it
assert C.__module__ == __name__

# NFKC normalization of the class name (line 3309)
assert unicodedata.normalize("NFKC", "\u2102") == "C"
assert make_class("\u2102", ["a"]).__name__ == "C"

# a non-list, non-dict attrs argument is rejected before any class exists
try:
    make_class("Bad", 42)
except TypeError as e:
    assert "attrs argument must be a dict or a list." in str(e)
else:
    raise AssertionError("make_class accepted a non-dict, non-list attrs argument")

# __attrs_post_init__ is popped out of the attrs mapping into the class body
def _post(self):
    self.seen = True

D = make_class("D", {"a": attrib(), "__attrs_post_init__": _post}, slots=False)
assert [f.name for f in fields(D)] == ["a"]
assert hasattr(D, "__attrs_post_init__")
assert D(1).seen is True

print("chapter 7 proof OK")
