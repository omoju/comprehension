"""Replays the scenario through the end of Chapter 3's span (trace lines 130-163):
Console.options -> ConsoleOptions.update -> Console.get_style('bold red')."""

from rich.color import ColorType
from rich.console import Console, ConsoleDimensions, NO_CHANGE
from rich.errors import MissingStyle

console = Console(record=True, width=100)

# The first print of the scenario; its internals are what this chapter follows.
console.print("Hello", "World!", style="bold red")

# --- trace 131-138: Console.size -------------------------------------------
size = console.size
assert isinstance(size, ConsoleDimensions)
assert size.width == 100  # pinned by width=100, not detected

# --- trace 130-147: Console.options ----------------------------------------
options = console.options
assert options.min_width == 1
assert options.max_width == 100
assert options.is_terminal is False
assert options.legacy_windows is False
assert options.encoding == "utf-8"          # trace 139-142
assert options.ascii_only is False          # because encoding startswith "utf"
assert options.max_height == size.height
assert options.justify is None
assert options.overflow is None
assert options.height is None
assert options.no_wrap is False             # dataclass default, before update()

# --- trace 148-151: ConsoleOptions.update with the args print passes --------
updated = options.update(
    justify=None,
    overflow=None,
    width=NO_CHANGE,
    height=None,
    no_wrap=None,
    markup=None,
    highlight=None,
)
assert updated is not options               # update() copies, trace 149-150
assert options.no_wrap is False             # original untouched
assert updated.no_wrap is None              # None is a value, not "no change"
assert updated.max_width == 100             # NO_CHANGE left the widths alone
assert updated.min_width == 1
assert updated.max_height == size.height    # height=None does not touch max_height

# --- trace 152-163: Console.get_style('bold red') --------------------------
style = console.get_style("bold red")
assert style.bold is True
assert style.color is not None
assert style.color.name == "red"
assert style.color.type is ColorType.STANDARD
assert style.color.number == 1              # trace 158
assert style.bgcolor is None
assert style.link is None                   # trace 161-162: so no copy is made
assert str(style) == "bold red"

# Style.parse is lru_cached and the no-link path hands back the cached object.
assert console.get_style("bold red") is style

# An unparseable definition is a loud failure, unless a default is supplied.
try:
    console.get_style("bold rodd")
except MissingStyle:
    pass
else:
    raise AssertionError("expected MissingStyle for an unparseable style")
assert console.get_style("bold rodd", default="bold red") is style
