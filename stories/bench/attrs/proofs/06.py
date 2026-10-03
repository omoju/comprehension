"""Chapter 6: attrs.asdict over the README instance. Run from the repo root with PYTHONPATH=src."""

import attr

from attr import fields
from attr._funcs import _ATOMIC_TYPES, _asdict_anything, has
from attrs import Factory, asdict, define


@define
class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


sc = SomeClass(1, [1, 2, 3])

# The instance carries no __dict__; the field list comes off the class.
assert not hasattr(sc, "__dict__")
assert [a.name for a in fields(SomeClass)] == ["a_number", "list_of_numbers"]

# a_number takes the atomic fast path; list_of_numbers does not.
assert type(sc.a_number) in _ATOMIC_TYPES
assert type(sc.list_of_numbers) not in _ATOMIC_TYPES

# has(list) -> False, so the collection branch is chosen (trace lines 144-147).
assert has(list) is False

# Each element goes through _asdict_anything and comes back unchanged.
assert (
    _asdict_anything(
        1,
        is_key=False,
        filter=None,
        dict_factory=dict,
        retain_collection_types=True,
        value_serializer=None,
    )
    == 1
)

d = asdict(sc)
assert d == {"a_number": 1, "list_of_numbers": [1, 2, 3]}

# The collection is rebuilt: a new list object, same elements (shallow copy).
assert d["list_of_numbers"] is not sc.list_of_numbers
assert d["list_of_numbers"] == sc.list_of_numbers

# The two namespaces differ exactly in retain_collection_types.
@define
class WithTuple:
    t: tuple = ()


w = WithTuple((1, 2))
assert asdict(w)["t"] == (1, 2)
assert isinstance(asdict(w)["t"], tuple)
assert attr.asdict(w)["t"] == [1, 2]
assert isinstance(attr.asdict(w)["t"], list)

# asdict reads the field *name*, not the __init__ alias.
@define
class Private:
    _x: int = 0


assert asdict(Private(7)) == {"_x": 7}

print("chapter 6 proof OK")
