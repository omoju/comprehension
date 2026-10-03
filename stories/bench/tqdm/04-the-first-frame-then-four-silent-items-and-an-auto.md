# Chapter 4 · The first frame, four items, and an automatic close

> **Enters as:** the four strings on a bar with `n=0`, `total=4`, `pos=0`, `sp` ready, and no `start_t` yet — entering `tqdm.refresh(self, nolock=False, lock_args=None)`

The last statement of `__init__` before the clocks are set is `self.refresh(lock_args=self.lock_args)` ([std.py#L1102-L1103](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1102-L1103)). `lock_args` is `None`, so `refresh` takes the plain blocking path:

```python
if not nolock:
    if lock_args:
        if not self._lock.acquire(*lock_args):
            return False
    else:
        self._lock.acquire()
self.display()
```

([std.py#L1345-L1357](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1345-L1357)). The trace shows exactly that: `acquire`, `display`, `release`, return `True`. The same process-wide lock from Chapter 1, now guarding the screen rather than the registry.

> **For the owner:** `lock_args` changes a guarantee. With it set (e.g. `lock_args=(False,)` for a non-blocking acquire), a bar that loses the race prints nothing and `refresh` returns `False` instead of waiting. That is the correct choice for many parallel bars — contention never stalls the workers — but it means frames are silently dropped. Decide per use whether a dropped frame or a blocked worker is the worse outcome.

## Deciding there is a line to draw on

`display(msg=None, pos=None)` first resolves `pos = abs(self.pos)` → `0`, then applies the screen-height rule:

```python
nrows = self.nrows or 20
if pos >= nrows - 1:
    if pos >= nrows:
        return False
    if msg or msg is None:  # override at `nrows - 1`
        msg = " ... (more hidden) ..."
```

([std.py#L1484-L1492](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1484-L1492)). `nrows` came back `None` from the terminal probe in Chapter 2, so the fallback 20 applies; at `pos=0` nothing is hidden. A bar on line 20 or beyond would simply not be drawn — `display` returns `False` and no exception is raised. That is deliberate: deeply nested bars go quiet rather than scrolling the terminal.

`self.sp` exists (Chapter 3), so the deprecation branch for `gui=True` is skipped ([std.py#L1494-L1498](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1494-L1498)), and because `pos` is `0` the two `moveto` calls that would walk the cursor down and back up are skipped too ([std.py#L1500-L1504](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1500-L1504)). What remains is `self.sp(self.__str__())`.

## A snapshot, then pure formatting

`__str__` is one line: `return self.format_meter(**self.format_dict)` ([std.py#L1156-L1157](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1156-L1157)). The split matters: `format_dict` reads mutable bar state once, and `format_meter` is a `@staticmethod` that turns that snapshot into a string without touching the instance.

The snapshot the trace records is `{'ascii': False, 'bar_format': None, 'colour': None, 'elapsed': 0, 'initial': 0, 'n': 0, ...}`. Two entries are worth reading closely:

- `'elapsed': 0`, because of `self._time() - self.start_t if hasattr(self, 'start_t') else 0` ([std.py#L1463](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1463)). `start_t` is still unassigned — Chapter 3's deliberate ordering — so the first frame honestly reports zero elapsed time rather than a number measured from a clock that does not exist yet.
- `rate`, from `self._ema_dn() / self._ema_dt() if self._ema_dt() else None` ([std.py#L1466](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1466)). The trace shows a single `EMA.__call__(x=None)` returning `0`: with `calls == 0` the estimator returns its initial `last` ([std.py#L228-L239](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L228-L239)), the `if` short-circuits, `_ema_dn` is never consulted, and `rate` is `None`.

`format_meter(n=0, total=4, elapsed=0, ncols=None, prefix='', ascii=False, ...)` then runs its gauntlet of degradations. `elapsed` is falsy, so the `rate = (n - initial) / elapsed` fallback never divides by zero ([std.py#L550-L551](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L550-L551)); with no rate, the formatter emits `'?it/s'` and the remaining-time field becomes `'?'` rather than an invented ETA ([std.py#L552-L574](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L552-L574)). `prefix` is empty, so `l_bar` starts bare and `format_interval(0)` gives `'00:00'` ([std.py#L397-L415](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L397-L415)).

`total` is truthy, so the predictive branch runs: `frac = 0.0`, `percentage = 0.0`, `l_bar = '  0%|'`. Before building a bar, the formatter probes with a sentinel:

```python
full_bar = FormatReplace()
nobar = bar_format.format(bar=full_bar, **format_dict)  # no `{bar}`
if not full_bar.format_called:
    return disp_trim(nobar, ncols) if ncols else nobar
```

([std.py#L630-L633](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L630-L633)). `FormatReplace.__format__` just counts calls and returns its replacement string ([utils.py#L85-L97](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L85-L97)); the trace shows one such call. The default format does reference `{bar}`, so the real `Bar` gets built — `Bar(frac=0.0, default_len=10, charset=' ▏▎▍▌▋▊▉█', colour=None)`, the width being the fixed 10 precisely because `ncols` is unknown ([std.py#L636-L639](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L636-L639)). Rendering it is `divmod` arithmetic over the charset: zero full blocks, so ten spaces ([std.py#L202-L208](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L202-L208)). The two `_is_ascii` calls in the trace are the short-circuit pair at [std.py#L640-L641](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L640-L641): the charset is not ASCII, the format string is, so it is coerced to `str` — a no-op here.

Out comes `'  0%|          | 0/4 [00:00<?, ?it/s]'`, returned untrimmed because `ncols` is falsy ([std.py#L642-L643](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L642-L643)).

## Thirty-seven characters, plus a carriage return

`print_status` measures the line with `disp_len` → `_text_width` → `37` ([utils.py#L303-L312](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L303-L312)) — ANSI codes stripped, East-Asian wide characters counted double, neither present here. `last_len[0]` is still `0`, so `max(0 - 37, 0)` adds no padding, and `fp_write('\r' + s)` sends 38 characters. The write goes through `DisableOnWriteError.disable_on_exception.<locals>.inner`, which returns `38`, followed by the elided flush ([utils.py#L177-L194](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L177-L194)). Every frame from here on travels that same error-swallowing path.

`display` returns `True`, `refresh` releases the lock and returns `True`, and `__init__` finally sets `last_print_t` and `start_t` ([std.py#L1106-L1108](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1106-L1108)). The bar is now visible to the monitor thread, and `tqdm(chars)` returns.

## Four items, handed back exactly as they came

The caller's `for char in ...` drives `__iter__`. Its first act is the disabled shortcut — `yield from iterable; return`, with no bookkeeping at all ([std.py#L1172-L1176](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1172-L1176)) — then it copies `mininterval`, `last_print_t`, `last_print_n`, `n` and `self._time` into locals for speed, and computes `min_start_t = self.start_t + self.delay` ([std.py#L1178-L1183](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1178-L1183)).

The loop body yields first and counts afterwards:

```python
for obj in iterable:
    yield obj
    n += 1
    if n - last_print_n >= self.miniters:
        cur_t = time()
        dt = cur_t - last_print_t
        if dt >= mininterval and cur_t >= min_start_t:
            self.update(n - last_print_n)
```

([std.py#L1186-L1198](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1186-L1198)). The trace records this as `tqdm.__iter__(self) → 'a'` and then `… tqdm.__iter__ ×4 more`: four yields of the original objects — `'a'`, `'b'`, `'c'`, `'d'`, unchanged, which is why the caller's `text` ends up `"abcd"` — plus a fifth resumption where the list is exhausted. Note the two gates: a cheap counter comparison first, so `time()` is not called on every iteration, and only then the clock. Nothing is printed unless both open. The second bar's trace opens this machinery up frame by frame; this chapter's remaining resumptions are collapsed into one line, so the frames the first bar drew along the way are not visible here.

What *is* visible is the exit:

```python
finally:
    self.n = n
    self.close()
```

([std.py#L1199-L1201](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1199-L1201)). The published counter is reconciled with the loop's private one — `n = 4` — and the bar closes itself. Because it is a `finally`, this also runs on `break` and on an exception propagating out of the loop body: the terminal is restored even when the loop aborts. With `leave=True` (the default), `close` draws one last frame at position 0 and writes `'\n'` ([std.py#L1303-L1314](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1303-L1314)) — which is how the `0/4` line stops being the last word on screen.

Then, later, garbage collection: `tqdm.__del__` → `close()` → `None`, with no children in the trace at all. That emptiness is the evidence. `close` opens with

```python
if getattr(self, 'disable', True):
    return
self.disable = True
```

([std.py#L1270-L1276](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1270-L1276)), so a second call does nothing — meaning (inference from the code plus the empty call) `disable` was already `True` when `__del__` fired, i.e. the `finally` had already done the work. The `getattr` default of `True` also covers an object that died before `__init__` finished.

> **For the owner:** Cleanup is guaranteed, but its *timing* is not. The `finally` in `__iter__` closes the bar deterministically when a loop ends or breaks; a bar created outside a loop and never closed is tidied only by `__del__`, at an unpredictable moment, which can put the final frame in the middle of unrelated output. Require `with tqdm(...) as t:` — whose `__exit__` calls `close()` and tolerates a late `AttributeError` with a warning ([std.py#L1141-L1151](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1141-L1151)) — or an explicit `close()` in any code that holds a bar across function boundaries.

> **Leaves as:** `'a'`, `'b'`, `'c'`, `'d'` handed back to the caller unchanged (`text == "abcd"`), the bar carrying `n = 4` and `disable = True` after its own `finally` closed it, and `__del__`'s second `close()` returning `None` immediately
