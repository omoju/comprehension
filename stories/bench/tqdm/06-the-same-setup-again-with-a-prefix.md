# Chapter 6 · The same setup again, with a prefix

> **Enters as:** `tqdm.__init__(self=<tqdm object at 0x109a02210>, iterable=['a', 'b', 'c', 'd'], desc='Processing', total=None, leave=True, file=None, ncols=None, mininterval=0.1, maxinterval=10.0, miniters=None, ascii=None, disable=False, unit='it', unit_scale=False, dynamic_ncols=False, smoothing=0.3, bar_format=None, initial=0, position=None, postfix=None, unit_divisor=1000, write_bytes=False, lock_args=None, nrows=None, colour=None, delay=0.0, gui=False)`

The list arrives at the same door it went through in Chapters 2 and 3, and the sequence is identical, step for step. That sameness is the point of this chapter: initialisation is not adaptive. Whatever the caller passes, `__init__` runs one fixed script — wrap the stream, infer `total`, probe the terminal, detect Unicode, build the smoothers, claim a line under the lock, build the printer, paint one frame. Only one argument differs from the first bar, and it travels all the way to the left edge of the output.

## The same seven steps, in the same order

The stream wrapping comes first. `file is None` so it becomes `sys.stderr` ([std.py#L968-L969](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L968-L969)), then `file = DisableOnWriteError(file, tqdm_instance=self)` ([std.py#L977](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L977)). The trace shows the wrapper being built fresh — `ObjectWrapper.__init__` stashing `_wrapped`, then two `disable_on_exception` closures installed over `write` and `flush` ([utils.py#L196-L203](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L196-L203)), this time bound by weak proxy to the *new* instance at `0x109a02210`. Each bar gets its own guard; they are not shared.

Then `total`. The caller passed `total=None` and an iterable, so the same borrowing happens:

```python
if total is None and iterable is not None:
    try:
        total = len(iterable)
    except (TypeError, AttributeError):
        total = None
```

([std.py#L982-L986](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L982-L986)). `len(['a','b','c','d'])` is 4, and the trace confirms it downstream: `format_meter(n=0, total=4, ...)`.

Then the terminal probe. `ncols` and `nrows` are both `None` and `file` compares equal to `sys.stderr` — that equality is `DisableOnWriteError.__eq__` unwrapping itself ([utils.py#L205-L206](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L205-L206)), returning `True` in the trace — so the else-branch calls `_screen_shape_wrapper()` and then its inner ([std.py#L1022-L1029](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1022-L1029)). It returns `(None, None)` again: `get_terminal_size` on a redirected stderr raises, and the bare `except Exception: return None, None` absorbs it ([utils.py#L270-L276](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L270-L276)). So `ncols` stays `None` — a 10-cell bar and no trimming — and `nrows` stays `None`, which `display` will later read as the fallback 20.

Then Unicode: `ascii is None`, so `ascii = not _supports_unicode(file)` ([std.py#L1043-L1044](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1043-L1044)); the wrapper forwards `.encoding` as `'utf-8'`, `_is_utf` says `True`, so `ascii` becomes `False` and the bar will use the smooth block charset.

Then the smoothers: three `EMA(0.3)` objects for increments, intervals, and miniters ([std.py#L1076-L1078](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1076-L1078)), each starting at `last = 0, calls = 0`.

## The one difference: `desc` becomes a prefix

The new argument is stored in a single line:

```python
self.desc = desc or ''
```

([std.py#L1055](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1055)). `'Processing'` survives verbatim — no colon appended here. `format_dict` then publishes it under the key `prefix` ([std.py#L1464](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1464)), which is how the trace shows it reaching the renderer: `format_meter(..., prefix='Processing', ...)`. The colon is added at render time:

```python
if prefix:
    # old prefix setup work around
    bool_prefix_colon_already = (prefix[-2:] == ": ")
    l_bar = prefix if bool_prefix_colon_already else prefix + ": "
else:
    l_bar = ''
```

([std.py#L582-L587](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L582-L587)). `'Processing'` does not end in `': '`, so it becomes `'Processing: '`. That check is what keeps `set_description` (which *does* append `': '`) from producing `'Processing a: : '` in Chapter 7. An empty `desc` takes the other branch and also strips a literal `'{desc}: '` out of any custom `bar_format` ([std.py#L624-L626](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L624-L626)), which is why the first bar's frame began with two spaces and a percentage rather than a stray colon.

## Position 0, free again

Under the global lock:

```python
with self._lock:
    # mark fixed positions as negative
    self.pos = self._get_free_pos(self) if position is None else -position
```

([std.py#L1095-L1097](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1095-L1097)). `_get_free_pos` collects `abs(inst.pos)` over every live instance except this one and returns the smallest non-negative integer not in that set ([std.py#L680-L685](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L680-L685)). The trace records `→ 0`. The first bar had held position 0; it is free now not because it was garbage-collected but because its `close()` ran `_decr_instances`, which removes the instance from `_instances` under the lock ([std.py#L697-L703](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L697-L703)).

> **For the owner:** Line positions are reclaimed by `close()`, not by garbage collection, because `_get_free_pos` reads the registry that `_decr_instances` empties. A bar that is abandoned without closing keeps its slot until it is collected, so the next bar is pushed to the line below. Require `with tqdm(...)` or an explicit `close()` in code that creates bars in a loop.

## The printer and the first frame

`gui=False`, so the screen printer is built and, since `delay <= 0`, the bar paints immediately ([std.py#L1099-L1103](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1099-L1103)). `status_printer` closes over `last_len = [0]` and pads each write to erase whatever was longer before it ([std.py#L453-L459](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L453-L459)) — a fresh, zeroed memory for this bar, independent of the one the first bar used.

`refresh` takes the lock, calls `display`, releases ([std.py#L1345-L1357](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1345-L1357)); `display` calls `self.__str__()`, which is `format_meter(**self.format_dict)` ([std.py#L1156-L1157](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1156-L1157)). The snapshot handed over is `n=0, total=4, elapsed=0, rate=None` — `rate` is `None` because `self._ema_dt()` is still `0` ([std.py#L1466](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1466)) — so the time fields render as `?`. A `FormatReplace` sentinel probes whether `{bar}` is used at all before the real `Bar` is built ([std.py#L630-L639](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L630-L639)); it is, and `Bar.__format__` at `frac=0.0` yields ten spaces ([std.py#L202-L208](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L202-L208)).

The result is `'Processing:   0%|          | 0/4 [00:00<?, ?it/s]'`. `disp_len` measures it at 49 columns — ANSI stripped, East-Asian wide characters counted double ([utils.py#L307-L312](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L307-L312)) — and `fp_write` emits `'\r' + s`, 50 characters, through the error-swallowing wrapper.

> **For the owner:** Two bars sharing stderr do not share the padding state that makes in-place updates work; each `status_printer` tracks its own `last_len`. Overlap is prevented only by distinct positions and the global write lock, so any code that writes to stderr outside tqdm (plain `print(file=sys.stderr)`) will garble the bar. Direct contributors to `tqdm.write` or the `external_write_mode` context manager instead.

Initialisation closes by stamping the clock, deliberately last: `self.last_print_t = self._time()` and then `self.start_t = self.last_print_t`, with the comment `NB: Avoid race conditions by setting start_t at the very end of init` ([std.py#L1106-L1108](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1106-L1108)). Until that assignment the monitor thread from Chapter 5 would have skipped this instance; from here on it is a legitimate candidate for a forced refresh.

> **Leaves as:** a fully initialised bar — `iterable=['a','b','c','d']`, `desc='Processing'`, `total=4`, `pos=0`, `ncols=None`, `nrows=None`, `ascii=False`, `miniters=0` with `dynamic_miniters=True`, `n=0`, `last_print_n=0`, `start_t` set — having written one 50-character frame `'\rProcessing:   0%|          | 0/4 [00:00<?, ?it/s]'` to stderr, and ready for the caller's `for char in pbar:`
