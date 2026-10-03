"""Chapter 2: ('Hello', 'World!') -> [<text 'Hello World!' [] ''>]."""

from rich.console import Console
from rich.control import strip_control_codes
from rich.highlighter import ReprHighlighter
from rich.markup import render as render_markup
from rich.protocol import rich_cast
from rich.text import Text
from rich._emoji_codes import EMOJI
from rich._emoji_replace import _emoji_replace

console = Console(record=True, width=100)

# --- the admission gate: a str comes back from rich_cast unchanged -----------
assert rich_cast("Hello") == "Hello"

# --- markup.render takes the fast path when there is no "[" -----------------
fast = render_markup("Hello", "", emoji=True, emoji_variant=None)
assert isinstance(fast, Text)
assert fast.plain == "Hello"
assert fast.spans == []

# --- emoji substitution runs, and unknown codes are returned verbatim -------
assert _emoji_replace("Hello") == "Hello"
assert _emoji_replace(":definitely_not_an_emoji_name:") == ":definitely_not_an_emoji_name:"
_name = "vampire" if "vampire" in EMOJI else next(iter(EMOJI))
assert _emoji_replace(f":{_name}:") == EMOJI[_name]

# --- every Text strips the five control codes -------------------------------
assert strip_control_codes("a\rb\x07c\x08d") == "abcd"
assert Text("a\rb").plain == "ab"
assert Text("esc:\x1b[31m").plain == "esc:\x1b[31m"  # ESC is NOT stripped

# --- render_str: 'Hello' and 'World!' each become a span-less Text ----------
hello = console.render_str("Hello", highlighter=console.highlighter)
world = console.render_str("World!", highlighter=console.highlighter)
assert (hello.plain, len(hello), hello.spans) == ("Hello", 5, [])
assert (world.plain, len(world), world.spans) == ("World!", 6, [])

# --- highlighting really did run; it just matched nothing here --------------
assert ReprHighlighter()("Hello").spans == []
numbered = console.render_str("1234", highlighter=console.highlighter)
assert any(span.style == "repr.number" for span in numbered.spans)

# --- _collect_renderables joins them with sep into exactly one Text ---------
renderables = console._collect_renderables(("Hello", "World!"), " ", "\n")
assert len(renderables) == 1
text = renderables[0]
assert isinstance(text, Text)
assert text.plain == "Hello World!"
assert text.spans == []
assert len(text) == 12          # 5 + 1 (sep) + 6
assert text.style == ""
assert text.end == "\n"         # inherited from the separator's blank_copy

# --- join rewrites span offsets rather than dropping them -------------------
joined = Text(" ").join([Text("Hello", style="bold"), Text("World!")])
assert joined.plain == "Hello World!"
assert (joined.spans[0].start, joined.spans[0].end, joined.spans[0].style) == (0, 5, "bold")

# --- nothing has been written yet: we are still inside the buffer transaction
assert console._buffer == []
assert console._record_buffer == []

print("chapter 2 ok")
