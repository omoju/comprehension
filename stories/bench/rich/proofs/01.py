"""Chapter 1: constructing the Console the scenario's data will travel through."""
import io
import sys

from rich.console import Console
from rich.highlighter import ReprHighlighter

# --- exactly as the scenario constructs it -------------------------------
console = Console(record=True, width=100)

# Width is pinned by the caller, independent of the real terminal.
assert console._width == 100
assert console.width == 100, console.width
assert console.size == (100, 25) or console.size.width == 100

# Jupyter / legacy-Windows probes both answered "no" in the trace.
assert console.is_jupyter is False
if sys.platform != "win32":
    assert console.legacy_windows is False

# Recording is on, and starts empty: nothing has been printed yet.
assert console.record is True
assert console._record_buffer == []

# The log renderer is built eagerly with the logging defaults (unused by print).
assert console._log_render.show_time is True
assert console._log_render.show_path is True
assert console._log_render.show_level is False
assert console._log_render.time_format == "[%X]"
assert console._log_render._last_time is None

# The default theme stack is in place and thread-local alongside the buffer.
assert console._theme_stack is console._thread_locals.theme_stack
assert console._theme_stack.get("repr.number") is not None
assert console._thread_locals.buffer == []
assert console._thread_locals.buffer_index == 0

# Defaults the scenario relies on later.
assert console._markup is True
assert console._emoji is True
assert console._highlight is True
assert isinstance(console.highlighter, ReprHighlighter)
assert console.safe_box is True
assert console.file is sys.stdout

# --- the colour decision, made deterministic -----------------------------
# A StringIO sink reports isatty() == False, exactly as stdout did in the trace,
# so 'auto' detection must settle on "no colour system at all".
not_a_tty = io.StringIO()
assert not_a_tty.isatty() is False
plain = Console(record=True, width=100, file=not_a_tty, _environ={})
assert plain.is_terminal is False
assert plain.is_dumb_terminal is False
assert plain._color_system is None
assert plain.color_system is None

# Overriding the probe flips the decision for an otherwise identical console.
forced = Console(width=100, file=io.StringIO(), force_terminal=True, _environ={})
assert forced.is_terminal is True
assert forced._color_system is not None

print("chapter 1 ok")
