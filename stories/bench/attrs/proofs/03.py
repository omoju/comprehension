"""Chapter 3: from _ClassBuilder.__init__ through make_unhashable."""

import attr._compat
import attr._make as _make

from attr import setters
from attr._make import _DEFAULT_ON_SETATTR, ClassProps, Factory, _ClassBuilder, attrib


class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


# Exactly the ClassProps that chapter 1 produced (trace line 27).
props = ClassProps(
    is_exception=False,
    is_slotted=True,
    has_weakref_slot=True,
    is_frozen=False,
    kw_only=ClassProps.KeywordOnly.NO,
    collected_fields_by_mro=True,
    added_init=True,
    added_repr=True,
    added_eq=True,
    added_ordering=False,
    hashability=ClassProps.Hashability.UNHASHABLE,
    added_match_args=True,
    added_str=False,
    added_pickling=True,
    on_setattr_hook=_DEFAULT_ON_SETATTR,
    field_transformer=None,
)

builder = _ClassBuilder(SomeClass, None, True, props, False)

# The fields harvested in chapter 2 arrived intact.
assert builder._attr_names == ("a_number", "list_of_numbers")
assert builder._base_names == set()

# The slotted path snapshots the whole original class dict.
assert "hard_math" in builder._cls_dict
assert builder._cls_dict["__attrs_attrs__"] is builder._attrs
assert builder._cls_dict["__attrs_props__"] is props

# The convert+validate hook removed itself: no field has either.
assert all(a.validator is None and a.converter is None for a in builder._attrs)
assert builder._on_setattr is None
assert props.on_setattr_hook is _DEFAULT_ON_SETATTR  # the record is unchanged

# ... but only because there was nothing to do. With a validator it survives.
class Other:
    pass

props_dict = ClassProps(
    is_exception=False,
    is_slotted=False,
    has_weakref_slot=True,
    is_frozen=False,
    kw_only=ClassProps.KeywordOnly.NO,
    collected_fields_by_mro=True,
    added_init=True,
    added_repr=True,
    added_eq=True,
    added_ordering=False,
    hashability=ClassProps.Hashability.UNHASHABLE,
    added_match_args=True,
    added_str=False,
    added_pickling=False,
    on_setattr_hook=_DEFAULT_ON_SETATTR,
    field_transformer=None,
)
other = _ClassBuilder(
    Other,
    {"x": attrib(validator=lambda i, a, v: None)},
    False,
    props_dict,
    False,
)
assert other._on_setattr is _DEFAULT_ON_SETATTR

# Not frozen, no pre/post init.
assert builder._frozen is False
assert "__setattr__" not in builder._cls_dict
assert builder._has_pre_init is False
assert builder._has_post_init is False

# getstate/setstate were written because added_pickling is True.
getstate = builder._cls_dict["__getstate__"]
setstate = builder._cls_dict["__setstate__"]


class Dummy:
    __slots__ = ("a_number", "list_of_numbers")


d = Dummy()
setstate(d, (1, [1, 2, 3]))  # legacy tuple state still loads
assert getstate(d) == {"a_number": 1, "list_of_numbers": [1, 2, 3]}

partial = Dummy()
setstate(partial, {"a_number": 7})  # missing key is skipped, not an error
assert partial.a_number == 7
assert not hasattr(partial, "list_of_numbers")

# add_repr queues a script; nothing is compiled yet.
assert builder.add_repr(None) is builder
assert builder._repr_added is True
repr_script, repr_globs, _ = builder._script_snippets[0]
assert "_compat.repr_context.already_repring" in repr_script
assert "return '...'" in repr_script
assert repr_globs["_compat"] is attr._compat
assert "__repr__" not in builder._cls_dict

# add_eq queues a type-exact __eq__ and attaches the shared __ne__.
assert builder.add_eq() is builder
eq_script = builder._script_snippets[1][0]
assert eq_script.splitlines()[:3] == [
    "def __eq__(self, other):",
    "    if other.__class__ is not self.__class__:",
    "        return NotImplemented",
]
assert eq_script.endswith("self.list_of_numbers == other.list_of_numbers\n    )")
assert builder._cls_dict["__ne__"] is _make.__ne__

# add_setattr finds nothing to hook and writes no __setattr__.
assert builder.add_setattr() is builder
assert "__setattr__" not in builder._cls_dict
assert "__attrs_own_setattr__" not in builder._cls_dict
assert builder._wrote_own_setattr is False

# UNHASHABLE -> __hash__ = None.
assert props.is_hashable is False
assert props.hashability is ClassProps.Hashability.UNHASHABLE
assert builder.make_unhashable() is builder
assert builder._cls_dict["__hash__"] is None

# Two snippets queued, and setters.NO_OP was never involved.
assert len(builder._script_snippets) == 2
assert builder._on_setattr is not setters.NO_OP
