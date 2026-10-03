"""Replays scenario setup through the second bar's __init__ (trace lines 136-226)."""
import io
import sys

from tqdm import tqdm
from tqdm.std import Bar
from tqdm.utils import DisableOnWriteError, disp_len

chars = ["a", "b", "c", "d"]

# --- Chapter 4 equivalent: the first bar runs and closes, freeing position 0.
buf1 = io.StringIO()
text = ""
for char in tqdm(chars, file=buf1):
    text = text + char
assert text == "abcd", text

# --- Chapters 5-6: the second bar, with a prefix.
buf = io.StringIO()
pbar = tqdm(chars, desc="Processing", file=buf)

# The lock is process-global class state, shared with the first bar (Ch. 5).
assert tqdm.get_lock() is tqdm._lock
# One monitor thread, still alive, so __new__ did not build another (Ch. 5).
assert tqdm.monitor is not None
assert tqdm.monitor.report() is True

# The one differing argument is stored verbatim: no colon appended here.
assert pbar.desc == "Processing"
assert pbar.format_dict["prefix"] == "Processing"

# `total` was borrowed from len(iterable).
assert pbar.total == 4
assert pbar.n == 0 and pbar.last_print_n == 0

# Stream wrapped per-bar in its own DisableOnWriteError; equality unwraps.
assert isinstance(pbar.fp, DisableOnWriteError)
assert pbar.fp == buf
assert pbar.fp is not getattr(tqdm, "_shared_fp", None)

# Terminal probe produced nothing -> no trimming, 10-cell bar, 20-row fallback.
assert pbar.ncols is None
assert pbar.nrows is None

# miniters=None turned on dynamic_miniters.
assert pbar.miniters == 0 and pbar.dynamic_miniters is True

# Position 0 was free because the FIRST bar's close() ran _decr_instances.
assert pbar.pos == 0

# The printer exists (gui=False) and start_t was stamped last.
assert callable(pbar.sp)
assert hasattr(pbar, "start_t") and pbar.start_t == pbar.last_print_t

# The first frame, exactly as the trace records it.
frame = tqdm.format_meter(n=0, total=4, elapsed=0, ncols=None,
                          prefix="Processing", ascii=False, unit="it",
                          unit_scale=False, rate=None, bar_format=None,
                          postfix=None, unit_divisor=1000, initial=0, colour=None)
assert frame == "Processing:   0%|          | 0/4 [00:00<?, ?it/s]", repr(frame)
assert disp_len(frame) == 49, disp_len(frame)
assert buf.getvalue().endswith("\r" + frame), repr(buf.getvalue()[-60:])
assert len("\r" + frame) == 50

# Bar at frac=0.0 is ten spaces of the unicode charset.
assert f"{Bar(0.0, 10, charset=Bar.UTF)}" == "          "

# The colon rule: an already-suffixed prefix is not doubled.
assert tqdm.format_meter(n=0, total=4, elapsed=0, prefix="Processing a: ",
                         ascii=False).startswith("Processing a:   0%")
# An empty prefix yields no leading colon at all.
assert tqdm.format_meter(n=0, total=4, elapsed=0, prefix="",
                         ascii=False).startswith("  0%|")

pbar.close()
print("chapter 6 verified", file=sys.stderr)
