"""Walk through the first example from attrs' README."""

import os
import sys


# Make the src-layout package importable when running from the repo root.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from attrs import Factory, asdict, define, make_class


@define
class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)

    def hard_math(self, another_number):
        return self.a_number + sum(self.list_of_numbers) * another_number


def main():
    sc = SomeClass(1, [1, 2, 3])
    print(repr(sc))

    result = sc.hard_math(3)
    print("hard_math(3) =", result)

    print("equal to twin:", sc == SomeClass(1, [1, 2, 3]))
    print("differs from other:", sc != SomeClass(2, [3, 2, 1]))

    as_dict = asdict(sc)
    print("asdict:", as_dict)

    defaults = SomeClass()
    print(repr(defaults))

    C = make_class("C", ["a", "b"])
    made = C("foo", "bar")
    print(repr(made))

    assert repr(sc) == "SomeClass(a_number=1, list_of_numbers=[1, 2, 3])"
    assert result == 19
    assert sc == SomeClass(1, [1, 2, 3])
    assert sc != SomeClass(2, [3, 2, 1])
    assert as_dict == {"a_number": 1, "list_of_numbers": [1, 2, 3]}
    assert repr(defaults) == "SomeClass(a_number=42, list_of_numbers=[])"
    assert repr(made) == "C(a='foo', b='bar')"


if __name__ == "__main__":
    main()
