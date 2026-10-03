"""Replays the scenario up to the end of chapter 7's span (trace lines 404-474)."""
from rich.console import Console
from rich.measure import Measurement
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

# --- trace 412-418: the table is recognised, not converted -------------------
renderables = console._collect_renderables(
    (table,), " ", "\n", justify=None, emoji=None, markup=None, highlight=None
)
assert renderables == [table], renderables
assert renderables[0] is table

# --- trace 419-440: options rebuilt and copied -------------------------------
options = console.options
assert options.size == (100, 25), options.size
assert options.max_width == 100
assert options.encoding == "utf-8"
assert options.is_terminal is False

render_options = options.update(
    justify=None, overflow=None, height=None, no_wrap=None, markup=None, highlight=None
)
assert render_options is not options
assert render_options.max_width == 100

# --- trace 448-454: the frame's budget ---------------------------------------
assert table._extra_width == 5, table._extra_width
measure_options = render_options.update_width(100 - table._extra_width)
assert measure_options.max_width == 95 and measure_options.min_width == 95

# --- trace 456-463: the fixed-width Date column ------------------------------
assert table.padding == (0, 1, 0, 1), table.padding
assert table._get_padding_width(0) == 2
date_column = table.columns[0]
assert date_column.width == 12
assert table._measure_column(console, measure_options, date_column) == Measurement(
    14, 14
)

# --- trace 465-470: all four widths, and the branches not taken --------------
assert table.expand is False
widths = table._calculate_column_widths(console, measure_options)
assert widths == [14, 35, 19, 16], widths
table_width = sum(widths) + table._extra_width
assert table_width == 89, table_width
assert table_width <= options.max_width  # no collapse was needed

# --- trace 471-474: the options every cell will be rendered under ------------
cell_options = render_options.update(
    width=table_width, highlight=table.highlight, height=None
)
assert cell_options.min_width == 89 and cell_options.max_width == 89
assert cell_options.highlight is False  # table turns auto-highlighting off
assert cell_options.height is None

# Markup inside a cell costs no width: tags are parsed away before measuring.
solo_cell = table.columns[1]._cells[1]
assert solo_cell == "[red]Solo[/red]: A Star Wars Story"
assert len(console.render_str(solo_cell).plain) == 23
assert widths[1] == 35  # driven by "Star Wars Ep. VIII: The Last Jedi" + padding
print("chapter 7 proof ok")
