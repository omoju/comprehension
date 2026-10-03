"""Replays the scenario and checks the values Chapter 9 claims."""
import io
from contextlib import redirect_stdout

from rich.cells import cell_len
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.table import Table

TOP = "┏" + "━" * 14 + "┳" + "━" * 35 + "┳" + "━" * 19 + "┳" + "━" * 16 + "┓"
BOTTOM = "└" + "─" * 14 + "┴" + "─" * 35 + "┴" + "─" * 19 + "┴" + "─" * 16 + "┘"

# --- the crop step, in isolation -------------------------------------------
# The top border is 89 cells wide, not 100: heavy box glyphs are one cell each.
assert len(TOP) == 89
assert cell_len(TOP) == 89
assert Segment(TOP, Style()).cell_length == 89
# Under length with pad=False, adjust_line_length copies the line unchanged.
assert Segment.adjust_line_length(
    [Segment(TOP, Style())], 100, style=None, pad=False
) == [Segment(TOP, Style())]

# --- styles are spent at Style.render --------------------------------------
header_style = Style.parse("bold magenta")
assert header_style.render("Date        ", color_system=None) == "Date        "
# ...and would not be, with a colour system:
assert header_style.render("Date        ") != "Date        "

# --- the scenario ----------------------------------------------------------
stdout = io.StringIO()
with redirect_stdout(stdout):
    console = Console(record=True, width=100)
    # stdout is not a tty here, so no colour system was detected.
    assert console._color_system is None
    assert console.width == 100

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
        "Dec 20, 2019",
        "Star Wars: The Rise of Skywalker",
        "$275,000,000",
        "$375,126,118",
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
    console.print(table)

    # Each print flushed and emptied the thread-local buffer.
    assert console._buffer == []

captured = stdout.getvalue()

# --- what actually reached the file ----------------------------------------
lines = captured.splitlines()
assert lines[0] == "Hello World!"
assert lines[1] == "Where there is a Will there is a way."
assert lines[2] == TOP
assert lines[-1] == BOTTOM
assert captured.endswith("┘\n")
# No ANSI anywhere: every Style.render returned its text unchanged.
assert "\x1b" not in captured
# Nothing was padded out to the console width.
assert max(len(line) for line in lines) == 89

# --- export_text reads back the recorded copy ------------------------------
exported = console.export_text()
assert exported == captured
assert "Star Wars: The Rise of Skywalker" in exported
assert "Solo: A Star Wars Story" in exported  # markup tags became spans, then nothing
assert "$1,332,539,889" in exported

# clear=True is the default: the record buffer is drained.
assert console._record_buffer == []
assert console.export_text() == ""

print("chapter 9 proof ok")
