"""Chapter 6: replay the scenario up to the end of table construction."""

from rich import box
from rich.console import Console
from rich.errors import NotRenderableError
from rich.padding import Padding
from rich.protocol import is_renderable
from rich.table import Table
from rich.text import Text

# --- Chapters 1-5, replayed ------------------------------------------------
console = Console(record=True, width=100)
console.print("Hello", "World!", style="bold red")
console.print(
    "Where there is a [bold cyan]Will[/bold cyan] there [u]is[/u] a [i]way[/i]."
)

# --- Chapter 6 begins: the container ---------------------------------------
table = Table(show_header=True, header_style="bold magenta")

assert table.columns == [] and table.rows == []
assert table.box is box.HEAVY_HEAD          # default, not supplied by caller
assert table.safe_box is None               # defer to the console
assert table.header_style == "bold magenta"
assert table.footer_style == "table.footer"
assert table.show_header is True and table.show_edge is True
assert table._padding == (0, 1, 0, 1)       # Padding.unpack((0, 1))
assert table.padding == (0, 1, 0, 1)
assert table.expand is False                # _expand False and width is None

# Padding.unpack's contract, including the branch the table did not take.
assert Padding.unpack((0, 1)) == (0, 1, 0, 1)
assert Padding.unpack(2) == (2, 2, 2, 2)
try:
    Padding.unpack((1, 2, 3))
except ValueError as error:
    assert "1, 2 or 4 integers required" in str(error)
else:
    raise AssertionError("3-tuple padding should have been rejected")

# --- Four columns ----------------------------------------------------------
table.add_column("Date", style="dim", width=12)
table.add_column("Title")
table.add_column("Production Budget", justify="right")
table.add_column("Box Office", justify="right")

assert [column.header for column in table.columns] == [
    "Date",
    "Title",
    "Production Budget",
    "Box Office",
]
assert [column._index for column in table.columns] == [0, 1, 2, 3]
assert [column.width for column in table.columns] == [12, None, None, None]
assert [column.justify for column in table.columns] == [
    "left",
    "left",
    "right",
    "right",
]
assert table.columns[0].style == "dim"
assert table.columns[1].style == ""          # style or ""
assert table.columns[0].header_style == ""   # header_style or ""
assert all(column.overflow == "ellipsis" for column in table.columns)
assert all(column.highlight is False for column in table.columns)
assert all(column.no_wrap is False for column in table.columns)
assert all(list(column.cells) == [] for column in table.columns)

# --- Three rows ------------------------------------------------------------
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

assert table.row_count == 3 and len(table.rows) == 3
assert table.rows[0].style is None and table.rows[0].end_section is False

assert list(table.columns[0].cells) == [
    "Dec 20, 2019",
    "May 25, 2018",
    "Dec 15, 2017",
]
assert list(table.columns[3].cells) == [
    "$375,126,118",
    "$393,151,347",
    "[bold]$1,332,539,889[/bold]",
]
# Cells are stored exactly as given: markup is still uninterpreted text.
assert table.columns[1]._cells[1] == "[red]Solo[/red]: A Star Wars Story"
assert all(
    isinstance(cell, str) and not isinstance(cell, Text)
    for column in table.columns
    for cell in column.cells
)
assert len(table.columns) == 4  # no column was added or removed by the rows

# --- The renderability gate, and the branches this run did not take --------
assert is_renderable("Dec 20, 2019") is True
assert is_renderable(Text("x")) is True
assert is_renderable(2019) is False

ragged = Table()
ragged.add_column("A")
ragged.add_column("B")
try:
    ragged.add_row("ok", 1234)           # int is not renderable
except NotRenderableError as error:
    assert "int" in str(error)
else:
    raise AssertionError("an int cell should have been rejected")
# Partial mutation: column A kept its cell, but no Row was recorded.
assert list(ragged.columns[0].cells) == ["ok"]
assert list(ragged.columns[1].cells) == []
assert ragged.row_count == 0

short = Table()
short.add_column("A")
short.add_column("B")
short.add_row("only one")               # padded with None -> ""
assert list(short.columns[1].cells) == [""]

grown = Table()
grown.add_column("A")
grown.add_row("1")
grown.add_row("1", "2")                 # extra value grows the table
assert len(grown.columns) == 2
assert list(grown.columns[1].cells) == [Text(""), "2"]
assert grown.row_count == 2

print("chapter 6 proof OK")
