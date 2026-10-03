"""Replay the README example through `@define` and assert what chapter 5 claims.

Run from the repository root with PYTHONPATH=src.
"""

import linecache
import types

from attr import _make
from attrs import Factory, define, fields


_ORIGINAL = {}


def capture(cls):
    """Grab the class object *before* @define sees it."""
    _ORIGINAL["cls"] = cls
    return cls


@define
@capture
class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


original = _ORIGINAL["cls"]

# --- the class you get back is not the class you wrote -------------------
assert SomeClass is not original
assert SomeClass.__name__ == original.__name__ == "SomeClass"
assert SomeClass.__bases__ == original.__bases__ == (object,)
# The discarded original holds only a weak reference to the replacement.
assert original.__attrs_base_of_slotted__() is SomeClass
assert "__attrs_base_of_slotted__" not in SomeClass.__dict__

# --- one compile unit, registered with linecache -------------------------
assert SomeClass.__qualname__ == "SomeClass"
filename = f"<attrs generated methods {SomeClass.__module__}.SomeClass>"
assert filename in linecache.cache

size, mtime, lines, cached_name = linecache.cache[filename]
source = "".join(lines)
assert mtime is None
assert cached_name == filename
assert size == len(source)

# All three snippets are in that single source, in registration order.
assert (
    source.index("def __repr__(self):")
    < source.index("def __eq__(self, other):")
    < source.index("def __init__(self")
)
assert (
    "def __init__(self, a_number=attr_dict['a_number'].default,"
    " list_of_numbers=NOTHING):" in source
)
assert "self.list_of_numbers = __attr_factory_list_of_numbers()" in source

# --- one merged globals dict shared by every generated method ------------
g = SomeClass.__init__.__globals__
assert SomeClass.__repr__.__globals__ is g
assert SomeClass.__eq__.__globals__ is g
assert g["__attr_factory_list_of_numbers"] is list
assert g["NOTHING"] is _make.NOTHING
assert set(g["attr_dict"]) == {"a_number", "list_of_numbers"}

# --- the attach hooks stamped the owning class's dunders -----------------
assert SomeClass.__repr__.__qualname__ == "SomeClass.__repr__"
assert SomeClass.__eq__.__qualname__ == "SomeClass.__eq__"
assert SomeClass.__init__.__qualname__ == "SomeClass.__init__"
assert SomeClass.__init__.__annotations__ == {
    "a_number": int,
    "list_of_numbers": list[int],
    "return": None,
}
# __ne__ was never generated: it is the plain module-level function.
assert SomeClass.__ne__ is _make.__ne__

# --- slots: field names plus a weakref slot, and no instance __dict__ ----
assert SomeClass.__slots__ == ("a_number", "list_of_numbers", "__weakref__")
# The class-body values are gone; slot descriptors occupy those names, and
# the defaults now live only on the Attributes.
assert isinstance(
    SomeClass.__dict__["a_number"], types.MemberDescriptorType
)
assert isinstance(
    SomeClass.__dict__["list_of_numbers"], types.MemberDescriptorType
)
assert fields(SomeClass).a_number.default == 42
assert isinstance(fields(SomeClass).list_of_numbers.default, Factory)
assert not hasattr(SomeClass(), "__dict__")

sc = SomeClass(1, [1, 2, 3])
assert repr(sc) == "SomeClass(a_number=1, list_of_numbers=[1, 2, 3])"
assert sc.hard_math(3) == 19

# Each instance gets a fresh list out of the Factory.
assert SomeClass().list_of_numbers == []
assert SomeClass().list_of_numbers is not SomeClass().list_of_numbers

# --- equality is type-exact; __ne__ forwards NotImplemented --------------
assert sc.__eq__(SomeClass(1, [1, 2, 3])) is True
assert sc.__eq__(SomeClass(2, [3, 2, 1])) is False
assert sc.__eq__(object()) is NotImplemented
assert sc.__ne__(SomeClass(2, [3, 2, 1])) is True  # trace lines 136-137
assert sc.__ne__(object()) is NotImplemented


# --- the closure repair that the class swap makes necessary --------------
@define
class Closured:
    x: int = 0

    def who(self):
        return __class__


assert Closured.who.__closure__ is not None
# Without cell rewriting this would still be the pre-@define class.
assert Closured().who() is Closured

print("chapter 5 holds")
