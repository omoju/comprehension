"""Chapter 8: widths -> cells -> box -> the first Segments of the table."""

from rich import box as box_module
from rich._pick import pick_bool
from rich.console import Console
from rich.padding import Padding
from rich.segment import Segment
from rich.style import Style
from rich.table import Table

console = Console(record=True, width=100)
console.print("Hello", "World!", style="bold red")
console.print(
    "Where there is a [bold cyan]Will[/bold cyan] there [u]is[/u] a [i]way[/i]."
)

table = Table(show_header=True, header_style="bold magenta")
table.add_column("Date", style="dim", width=12)
table.add_column("Title")
table.add_column("Production Budget", justify="right")
table.add_column("Box Office", justify="right")
table.add_row(
    "Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$275,000,000", "$375,126,118"
)
table.add_row(
    "May 25, 2018",
    "[red]Solo[/red]: A Star Wars Story",
    "$275,000,000",
    "$393,151,347",
)
table.add_row(
    "Dec 15, 2017",
    "Star Wars Ep. VIII: The Last Jedi",
    "$262,000,000",
    "[bold]$1,332,539,889[/bold]",
)

# --- what Chapter 7 handed over -------------------------------------------
options = console.options
assert table._extra_width == 5
widths = table._calculate_column_widths(
    console, options.update_width(options.max_width - table._extra_width)
)
assert widths == [14, 35, 19, 16]

render_options = options.update(
    width=sum(widths) + table._extra_width, highlight=table.highlight, height=None
)
assert render_options.max_width == 89
assert render_options.highlight is False

# --- the cell stream for the Date column ----------------------------------
cells = list(table._get_cells(console, 0, table.columns[0]))
assert len(cells) == 4  # header + 3 body rows, no footer

header_cell = cells[0]
assert header_cell.style == Style(color="magenta", bold=True)
assert header_cell.vertical == "top"
assert isinstance(header_cell.renderable, Padding)
assert header_cell.renderable.renderable == "Date"
pad = header_cell.renderable
assert (pad.top, pad.right, pad.bottom, pad.left) == (0, 1, 0, 1)

assert cells[1].style == Style(dim=True)  # column style, not the header style
assert cells[1].renderable.renderable == "Dec 20, 2019"
assert cells[3].renderable.renderable == "Dec 15, 2017"

# --- choosing the box characters ------------------------------------------
assert pick_bool(table.safe_box, console.safe_box) is True
assert render_options.ascii_only is False
assert table.box.substitute(render_options, safe=True) is box_module.HEAVY_HEAD

top = table.box.get_top(widths)
assert top == (
    "\u250f" + "\u2501" * 14
    + "\u2533" + "\u2501" * 35
    + "\u2533" + "\u2501" * 19
    + "\u2533" + "\u2501" * 16
    + "\u2513"
)
assert len(top) == 89

# --- the Segments themselves ----------------------------------------------
segments = list(table._render(console, render_options, widths))
header_style = Style(color="magenta", bold=True)
assert segments[0] == Segment(top, Style())
assert segments[1] == Segment("\n")
assert segments[2] == Segment("\u2503", Style())          # heavy head_left
assert segments[3] == Segment(" ", header_style)          # left padding
assert segments[4] == Segment("Date        ", header_style)
assert segments[5] == Segment(" ", header_style)          # right padding

texts = [segment.text for segment in segments]
assert "Title                            " in texts      # 35 - 2 padding
assert "Production Budget" in texts                       # 19 - 2 padding
assert "    Box Office" in texts                          # right justified
assert "Solo" in texts                                    # markup interpreted
assert "$1,332,539,889" in texts
assert segments[-1] == Segment("\n")
assert segments[-2].text.startswith("\u2514") and segments[-2].text.endswith("\u2518")
print("chapter 8 ok")
