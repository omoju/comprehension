"""Replay Console.print's render span for 'Hello', 'World!' with style='bold red'."""

import rich.errors
from rich.cells import cell_len
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from rich._wrap import divide_line

console = Console(record=True, width=100)

# --- state entering this chapter (Chapters 2 and 3) -------------------------
renderables = console._collect_renderables(("Hello", "World!"), " ", "\n")
assert len(renderables) == 1
text = renderables[0]
assert isinstance(text, Text)
assert text.plain == "Hello World!"
assert text.spans == []

options = console.options.update(
    justify=None, overflow=None, no_wrap=None, highlight=None, markup=None, height=None
)
assert options.max_width == 100
assert options.no_wrap is None

render_style = console.get_style("bold red")
assert render_style == Style(color="red", bold=True)

# --- the gate ---------------------------------------------------------------
# max_width < 1 yields nothing at all (recursion guard, not taken here).
assert list(console.render(Text("x"), options.update_width(0))) == []

# anything that is not a str and has no __rich_console__ is rejected.
try:
    list(console.render(object()))
except rich.errors.NotRenderableError:
    pass
else:
    raise AssertionError("expected NotRenderableError")

# --- measuring in cells -----------------------------------------------------
assert cell_len("Hello") == 5          # word without trailing space
assert cell_len("Hello ") == 6         # what the cursor advances by
assert cell_len("World!") == 6
assert cell_len("Hello World!") == 12
assert divide_line("Hello World!", 100, fold=True) == []   # no break positions

# wrap is a no-op at this width
lines = text.wrap(
    console, 100, justify="default", overflow="fold", tab_size=8, no_wrap=False
)
assert [line.plain for line in lines] == ["Hello World!"]

# --- Text.render fast path (no spans): text segment + end segment -----------
assert list(Text("Hello World!").render(console, end="\n")) == [
    Segment("Hello World!"),
    Segment("\n"),
]

# --- Console.render -> split_lines_terminator -------------------------------
render_iter = console.render(text, options)
split = list(Segment.split_lines_terminator(render_iter))
assert split == [([Segment("Hello World!")], True)]

line, add_new_line = split[0]
assert add_new_line is True

# --- apply_style: base style sits under the segment's own (absent) style ----
styled = list(Segment.apply_style(line, render_style))
assert styled == [Segment("Hello World!", render_style)]
assert styled[0].style is render_style          # Style._add short-circuits on None

new_segments = styled + [Segment.line()]
assert new_segments == [
    Segment("Hello World!", Style(color="red", bold=True)),
    Segment("\n"),
]

# --- the render generator is spent: resuming yields nothing -----------------
assert list(Segment.split_lines_terminator(render_iter)) == []

# --- and the ordering of style composition is base + segment ----------------
over = Style(color="cyan")
assert list(Segment.apply_style([Segment("x", over)], render_style)) == [
    Segment("x", Style(color="cyan", bold=True))   # 'cyan' beat the base 'red'
]

print("chapter 4 ok")
