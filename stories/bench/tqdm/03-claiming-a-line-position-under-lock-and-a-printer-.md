# Chapter 3 · Claiming a line: position under lock and a printer with a memory

> **Enters as:** the four strings held as `self.iterable` on a bar with `total=4`, `desc=''`, `ncols=None`, `nrows=None`, `gui=False`, and a `DisableOnWriteError` wrapping stderr

Two small assignments come first. `last_print_n` and `n` are both set from `initial`, which is `0` ([std.py#L1089-L1091](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1089-L1091)) — the published counter and the counter as of the last repaint, starting in agreement. The gap that will later open between them is the whole throttling story, but right now there is none.

Then the bar has to decide where on the screen it lives, and for that it needs the lock from Chapter 1.

## A line number, decided under the lock

The trace shows `TqdmDefaultWriteLock.__enter__` → `acquire`, then `_get_free_pos`, then `__exit__` → `release`. In source that is three lines:

```python
with self._lock:
    # mark fixed positions as negative
    self.pos = self._get_free_pos(self) if position is None else -position
```

([std.py#L1095-L1097](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1095-L1097)). `position` is `None` here, so the classmethod runs:

```python
positions = {abs(inst.pos) for inst in cls._instances
             if inst is not instance and hasattr(inst, "pos")}
return min(set(range(len(positions) + 1)).difference(positions))
```

([std.py#L680-L685](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L680-L685)). It walks the global `_instances` registry, skips the bar asking the question, collects the screen lines already taken, and returns the lowest non-negative integer not among them. This bar is the only live one, so `positions` is empty and the answer is `0` — the trace's return value.

Three details in those five lines are worth an owner's attention. The `hasattr(inst, "pos")` guard tolerates another thread's bar that is mid-`__init__` and has not claimed a line yet. The `abs()` means a bar pinned with `position=3` — stored as `-3` by the branch this run did not take — still occupies line 3 for allocation purposes; the sign is a flag meaning "fixed", and Chapter 9 will show that fixed bars are never moved when a neighbour closes. And the whole computation is done while holding the process-wide reentrant lock, so two threads creating bars at once cannot both be told "line 0".

> **For the owner:** Automatic positioning is correct only for bars that are registered and closed. A bar that is abandoned without `close()` keeps its line reserved until garbage collection drops it from the `WeakSet`, so long-lived leaked bars will push later bars down the screen. Require `with tqdm(...)` or an explicit `close()` in code you sign off on.

The lock is released immediately afterwards; it is held for the allocation only, not for the rest of initialisation.

## A printer, built once, that remembers

Next:

```python
if not gui:
    # Initialize the screen printer
    self.sp = self.status_printer(self.fp)
```

([std.py#L1099-L1101](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1099-L1101)). `gui` is `False`, so a printer is built. The `gui=True` path deliberately leaves `self.sp` unset: that is how GUI subclasses signal that they render elsewhere, and `display` checks for the missing attribute and raises a `TqdmDeprecationWarning` telling the caller to use `tqdm.gui.tqdm` instead of `tqdm(..., gui=True)` ([std.py#L1494-L1498](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1494-L1498)).

Inside `status_printer` the trace shows one call that looks out of place: `DisableOnWriteError.__eq__` against the real `TextIOWrapper`, returning `True`. That is this test:

```python
if fp in (sys.stderr, sys.stdout):
    getattr(sys.stderr, 'flush', lambda: None)()
    getattr(sys.stdout, 'flush', lambda: None)()
```

([std.py#L443-L447](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L443-L447)). The wrapper forwards equality to the object it wraps, so it still counts as stderr; both standard streams are flushed once up front, so whatever the program printed before the bar appeared is on screen before the bar starts overwriting lines.

Then two closures are built. `fp_write` writes `str(s)` and flushes ([std.py#L449-L451](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L449-L451)). Above it sits the one piece of state this printer owns:

```python
last_len = [0]

def print_status(s):
    len_s = disp_len(s)
    fp_write('\r' + s + (' ' * max(last_len[0] - len_s, 0)))
    last_len[0] = len_s
```

([std.py#L453-L459](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L453-L459)). A one-element list holding the on-screen length of the previous frame. Every frame begins with a carriage return and ends with enough spaces to erase whatever the last, possibly longer, frame left behind. That is the entire in-place-update mechanism: no cursor queries, no ANSI erase codes, just `\r` and padding — which is exactly why the README promises tqdm works anywhere `\r` and `\n` do, and why a line too long for the console breaks it. If the terminal wraps the line, the `\r` returns to the start of the *wrapped* fragment, not the start of the bar, and each refresh leaves a new line behind.

> **For the owner:** In-place updating is a guarantee only when each rendered line fits the console width. With `ncols` unknown (Chapter 2) nothing trims the line, so a long `desc` or postfix in a narrow or log-capturing console produces one line per refresh instead of one updating line. If output goes to a log collector rather than a terminal, set `disable=None` to suppress the bar on non-TTYs, or pin `ncols`.

The returned closure — `<function tqdm.status_printer.<locals>.print_status at 0x109b2bc40>` in the trace — is stored as `self.sp`. It is per-bar: a second bar sharing stderr gets its own `last_len`, so the two never confuse each other's padding. What keeps them from overwriting each other's *lines* is the position allocated a moment ago, plus the shared lock.

## What has not happened yet

The next statement is `if delay <= 0: self.refresh(...)` ([std.py#L1102-L1103](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1102-L1103)), and `delay` is `0.0`. Nothing has been drawn yet; the stream has been flushed but not written to.

And deliberately, two attributes still do not exist. `last_print_t` and `start_t` are assigned only after that first refresh returns, with a comment saying so explicitly ([std.py#L1106-L1108](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1106-L1108)). The monitor thread from Chapter 1 filters its working set with `hasattr(i, 'start_t')` ([\_monitor.py#L56-L60](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L56-L60)), so a bar that is registered but not finished is invisible to it. The ordering is the race avoidance.

The four strings have not moved. They are still a list behind `self.iterable`, and the bar that will report on them now has a line to write on and a function to write with.

> **Leaves as:** the same four strings on a bar with `pos = 0` (claimed under the global lock) and `self.sp = <print_status closure>` over the wrapped stderr — about to paint its first frame
