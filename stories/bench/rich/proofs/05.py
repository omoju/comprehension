import io

from rich import markup
from rich.console import Console
from rich.errors import MarkupError
from rich.cells import cell_len
from rich.segment import Segment
from rich.text import Span

file = io.StringIO()
console = Console(record=True, width=100, file=file)

# Chapter 1's world: no colour system was detected, width is pinned at 100.
assert console._color_system is None
assert console.is_terminal is False
assert console.width == 100

style = console.get_style("bold red")
assert str(style) == "bold red"

# The data as it enters this chapter (end of Chapter 4).
new_segments = [Segment("Hello World!", style), Segment("\n")]

# The crop: 12 cells against a width of 100, pad=False, so nothing changes.
assert cell_len("Hello World!") == 12
assert Segment("Hello World!", style).cell_length == 12
# The newline is split off before measuring, and measures zero cells anyway.
assert Segment("\n").cell_length == 0
assert Segment.adjust_line_length(
    [Segment("Hello World!", style)], 100, style=None, pad=False
) == [Segment("Hello World!", style)]
assert list(Segment.split_and_crop_lines(new_segments, 100, pad=False)) == [
    [Segment("Hello World!", style), Segment("\n")]
]
# ... and the crop really does cut when the line is too wide.
assert Segment.adjust_line_length(
    [Segment("Hello World!", style)], 5, style=None, pad=False
) == [Segment("Hello", style)]

# With color_system None, Style.render is the identity.
assert style.render("Hello World!", color_system=None) == "Hello World!"

# One print == one write + flush; buffer emptied, record buffer holds a copy.
console.print("Hello", "World!", style="bold red")
assert file.getvalue() == "Hello World!\n"
assert console._buffer == []
assert console._record_buffer == [Segment("Hello World!", style), Segment("\n")]

# The second string takes the full markup path: tags become spans, not text.
rendered = markup.render(
    "Where there is a [bold cyan]Will[/bold cyan] there [u]is[/u] a [i]way[/i]."
)
assert rendered.plain == "Where there is a Will there is a way."
assert rendered.spans == [
    Span(17, 21, "bold cyan"),
    Span(28, 30, "underline"),
    Span(33, 36, "italic"),
]

console.print(
    "Where there is a [bold cyan]Will[/bold cyan] there [u]is[/u] a [i]way[/i]."
)
assert file.getvalue() == "Hello World!\nWhere there is a Will there is a way.\n"
assert "\x1b" not in file.getvalue()
assert console._buffer == []

# Unbalanced markup is a loud failure raised from inside print.
try:
    console.print("[/bold]")
except MarkupError as error:
    assert "doesn't match any open tag" in str(error)
else:
    raise AssertionError("expected MarkupError")

# markup=False is the escape hatch: the tag is printed verbatim.
before = len(file.getvalue())
console.print("[/bold]", markup=False)
assert file.getvalue()[before:] == "[/bold]\n"
