import inspect as _inspect

import attrs
from attr._make import (
    _DEFAULT_ON_SETATTR,
    ClassProps,
    Factory,
    _determine_attrs_eq_order,
    _has_own_attribute,
)
from attrs import define, frozen


# Factory only remembers the callable; nothing is called yet.
f = Factory(list)
assert f.factory is list
assert f.takes_self is False

# The defaults that `define` brings to the door.
sig = _inspect.signature(define).parameters
assert sig["slots"].default is True
assert sig["auto_detect"].default is True
assert sig["auto_attribs"].default is None
assert sig["order"].default is False
assert sig["auto_exc"].default is True
assert sig["force_kw_only"].default is False
assert sig["on_setattr"].default is None

# Trace line 8-9: eq stays undecided, order is already settled.
assert _determine_attrs_eq_order(None, None, False, None) == (None, False)


# _has_own_attribute looks at cls.__dict__ only.
class _Plain:
    pass


assert _has_own_attribute(_Plain, "__eq__") is False
assert _has_own_attribute(_Plain, "__setattr__") is False


class _BaseWithEq:
    def __eq__(self, other):
        return True


class _Child(_BaseWithEq):
    pass


assert _has_own_attribute(_Child, "__eq__") is False  # inherited doesn't count


@define
class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


# Trace line 27: the ClassProps that came out of the door.
props = attrs.inspect(SomeClass)
assert props.is_exception is False
assert props.is_slotted is True
assert props.has_weakref_slot is True
assert props.is_frozen is False
assert props.kw_only is ClassProps.KeywordOnly.NO
assert props.collected_fields_by_mro is True
assert props.added_init is True
assert props.added_repr is True
assert props.added_eq is True
assert props.added_ordering is False
assert props.hashability is ClassProps.Hashability.UNHASHABLE
assert props.added_match_args is True
assert props.added_str is False
assert props.added_pickling is True
assert props.field_transformer is None

# Trace lines 7 & 27: the on_setattr hook `wrap` installed by itself.
assert props.on_setattr_hook is _DEFAULT_ON_SETATTR

# Trace lines 29-30 / 82-83: is_hashable is False.
assert props.is_hashable is False


# The road not taken: frozen-ness inherited + an explicit hook is an error.
@frozen
class _FrozenBase:
    x: int = 0


try:

    @define(on_setattr=lambda inst, attr, val: val)
    class _Sub(_FrozenBase):
        y: int = 0

except ValueError as e:
    assert "frozen-ness was inherited" in str(e)
else:
    raise AssertionError("expected ValueError for inherited frozen-ness")


# The road not taken: cache_hash on a class that won't be hashable.
try:

    @define(cache_hash=True)
    class _Bad:
        x: int = 0

except TypeError as e:
    assert "cache_hash" in str(e)
else:
    raise AssertionError("expected TypeError for cache_hash without hashing")

print("chapter 1 verified")
