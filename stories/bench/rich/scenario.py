"""Typical Rich usage, following the README: console markup + a table."""

from rich.console import Console
from rich.table import Table

# For more control over rich terminal content, construct a Console object.
console = Console(record=True, width=100)

# Styled output, both via the `style` argument and console markup.
console.print("Hello", "World!", style="bold red")
console.print(
    "Where there is a [bold cyan]Will[/bold cyan] there [u]is[/u] a [i]way[/i]."
)

# Build the table from the README.
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

console.print(table)

# Inspect what was actually rendered to the terminal.
output = console.export_text()

assert "Hello World!" in output
assert "Where there is a Will there is a way." in output
assert "Star Wars: The Rise of Skywalker" in output
assert "Solo: A Star Wars Story" in output
assert "$1,332,539,889" in output
