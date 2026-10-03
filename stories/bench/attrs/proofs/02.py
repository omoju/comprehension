"""Chapter 2: _transform_attrs harvests the fields. Run with PYTHONPATH=src."""

from attr._compat import _get_annotations
from attr._make import (
    ClassProps,
    Factory,
    _default_init_alias_for,
    _is_class_var,
    _transform_attrs,
)
from attr.exceptions import FrozenInstanceError, UnannotatedAttributeError
from attrs import field


class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


# The Factory in the class body only remembers the callable.
assert SomeClass.list_of_numbers.factory is list
assert SomeClass.list_of_numbers.takes_self is False

# What _transform_attrs reads off the class (trace: _get_annotations -> ...).
anns = _get_annotations(SomeClass)
assert list(anns) == ["a_number", "list_of_numbers"], anns
assert anns["a_number"] is int

# ClassVar screening is a string comparison.
assert _is_class_var(int) is False
assert _is_class_var(list[int]) is False
assert _is_class_var("typing.ClassVar[int]") is True
assert _is_class_var("'ClassVar[int]'") is True
# An unrecognized alias is NOT detected:
assert _is_class_var("tp.ClassVar[int]") is False

# The span of this chapter, run exactly as the trace records it.
attrs_tuple, base_attrs, base_attr_map = _transform_attrs(
    SomeClass, None, True, ClassProps.KeywordOnly.NO, True, None
)

assert base_attrs == []
assert base_attr_map == {}

# The generated tuple subclass, indexable and name-accessible.
assert type(attrs_tuple).__name__ == "SomeClassAttributes"
assert isinstance(attrs_tuple, tuple)
assert len(attrs_tuple) == 2
assert attrs_tuple.a_number is attrs_tuple[0]

# hard_math is not a field; only the annotated names are.
assert [a.name for a in attrs_tuple] == ["a_number", "list_of_numbers"]

a, lon = attrs_tuple

assert a.default == 42
assert a.type is int
assert a.alias == "a_number"
assert a.alias_is_default is True
assert a.kw_only is False
assert a.init is True
assert a.inherited is False
assert a.eq is True
assert a.eq_key is None
assert a.order is True
assert a.order_key is None
assert a.hash is None
assert a.converter is None
assert a.validator is None
assert dict(a.metadata) == {}

assert isinstance(lon.default, Factory)
assert lon.default.factory is list
assert lon.default.takes_self is False
assert lon.type == list[int]
assert lon.alias == "list_of_numbers"
assert lon.alias_is_default is True

# Attribute objects are frozen.
try:
    a.name = "nope"
except FrozenInstanceError:
    pass
else:
    raise AssertionError("Attribute should have been frozen")

# Default aliasing strips leading underscores.
assert _default_init_alias_for("_x") == "x"
assert _default_init_alias_for("a_number") == "a_number"


# The UnannotatedAttributeError that define()'s auto_attribs guess relies on
# is raised here, before anything is written to the class.
class Mixed:
    x: int = field()
    y = field()


try:
    _transform_attrs(Mixed, None, True, ClassProps.KeywordOnly.NO, True, None)
except UnannotatedAttributeError as e:
    assert "y" in str(e), e
else:
    raise AssertionError("expected UnannotatedAttributeError")

assert "__attrs_attrs__" not in Mixed.__dict__


# Mandatory-after-default is a ValueError at class-definition time.
class Ordered:
    a: int = 1
    b: int


try:
    _transform_attrs(
        Ordered, None, True, ClassProps.KeywordOnly.NO, True, None
    )
except ValueError as e:
    assert "No mandatory attributes allowed" in str(e), e
else:
    raise AssertionError("expected ValueError about attribute order")

print("chapter 2 proof OK")
