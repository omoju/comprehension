"""Replay the scenario and assert what chapter 8's span decided for class C."""

import inspect

from attr import NOTHING, attrib, fields
from attr._compat import _get_annotations
from attr._make import (
    ClassProps,
    _assign,
    _assign_with_converter,
    _collect_base_attrs_broken,
    _determine_setters,
    _determine_whether_to_implement,
    _transform_attrs,
)
from attrs import Factory, define, make_class


@define
class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


C = make_class("C", ["a", "b"])

# --- the ClassProps this span produced (trace line 173) --------------------
props = C.__dict__["__attrs_props__"]
assert props.is_slotted is False
assert props.collected_fields_by_mro is False
assert props.added_ordering is True
assert props.added_pickling is False
assert props.on_setattr_hook is None
assert props.hashability is ClassProps.Hashability.UNHASHABLE
assert props.kw_only is ClassProps.KeywordOnly.NO
assert props.added_init is True
assert props.added_repr is True
assert props.added_eq is True
assert props.is_frozen is False
assert props.is_exception is False
assert props.is_hashable is False

# ...and the mirror-image settings that @define chose in chapter 1.
sc_props = SomeClass.__dict__["__attrs_props__"]
assert sc_props.is_slotted is True
assert sc_props.collected_fields_by_mro is True
assert sc_props.added_ordering is False
assert sc_props.added_pickling is True
assert sc_props.on_setattr_hook is not None

# `added_pickling` came from `default=slots`, with auto_detect off.
assert (
    _determine_whether_to_implement(
        C, None, False, ("__getstate__", "__setstate__"), default=False
    )
    is False
)
assert "__getstate__" not in C.__dict__
assert "__setstate__" not in C.__dict__

# --- fields harvested from `these`, not from the class body ----------------
assert [a.name for a in fields(C)] == ["a", "b"]
assert [a.alias for a in fields(C)] == ["a", "b"]
assert all(a.default is NOTHING for a in fields(C))
assert all(a.type is None for a in fields(C))
assert all(a.kw_only is False for a in fields(C))
assert all(a.on_setattr is None for a in fields(C))
assert fields(C).__class__.__name__ == "CAttributes"
assert C.__annotations__ == {}


class _Bare:
    pass


_res = _transform_attrs(
    _Bare,
    {"a": attrib(), "b": attrib()},
    False,
    ClassProps.KeywordOnly.NO,
    False,
    None,
)
assert _get_annotations(_Bare) == {}
assert [a.name for a in _res.attrs] == ["a", "b"]
assert [a.alias for a in _res.attrs] == ["a", "b"]
assert _res.base_attrs == []
assert _res.base_attrs_map == {}
assert _res.attrs.__class__.__name__ == "_BareAttributes"

# --- the legacy base collection returned ([], {}) --------------------------
assert C.__mro__ == (C, object)
assert _collect_base_attrs_broken(C, {"a", "b"}) == ([], {})

# --- ordering methods attached directly, type-exact --------------------------
for _name in ("__lt__", "__le__", "__gt__", "__ge__"):
    assert _name in C.__dict__
    assert C.__dict__[_name].__qualname__ == f"C.{_name}"
    assert _name not in SomeClass.__dict__  # @define left order=False

assert (C("a", "b") < C("a", "c")) is True
assert C("a", "b").__lt__(42) is NotImplemented
assert C("a", "b").__eq__(42) is NotImplemented
try:
    C("a", "b") < 42
except TypeError:
    pass
else:
    raise AssertionError("ordering against a foreign type should raise")

# --- unhashable, and no custom __setattr__ ---------------------------------
assert C.__dict__["__hash__"] is None
try:
    hash(C("a", "b"))
except TypeError:
    pass
else:
    raise AssertionError("C should be unhashable")

assert "__setattr__" not in C.__dict__
assert getattr(C, "__attrs_own_setattr__", None) is None

# --- the two-line initializer ----------------------------------------------
assert _determine_setters(False, False, {}) == ((), _assign, _assign_with_converter)
assert _assign("a", "a", False) == "self.a = a"
assert _assign("b", "b", False) == "self.b = b"

_src = [ln.strip() for ln in inspect.getsource(C.__init__).splitlines() if ln.strip()]
assert _src == ["def __init__(self, a, b):", "self.a = a", "self.b = b"], _src
assert C.__init__.__annotations__ == {"return": None}
assert list(inspect.signature(C.__init__).parameters) == ["self", "a", "b"]
# globals were snapshotted from the defining module.
assert C.__init__.__globals__["SomeClass"] is SomeClass

# --- the two protocols added because the class had neither ------------------
assert C.__match_args__ == ("a", "b")
assert "__replace__" in C.__dict__
assert C.__dict__["__replace__"].__qualname__ == "C.__replace__"

print("chapter 8 proof OK")
