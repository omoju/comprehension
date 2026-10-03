# Chapter 9 · Closing down: leaving the registry, the truth about the rate, and reading a dead bar

> **Enters as:** the bar at `0x109a02210` with `n=4`, `last_print_n=4`, `pos=0`, `leave=True`, `disable=False`, screen showing `Processing d: 100%|██████████| 4/4 [00:00<00:00, 17.50it/s]`, and `StopIteration` arriving in the generator's `finally`

The `for` loop inside `__iter__` has nothing left to pull. Control falls into the two lines that were waiting the whole time ([std.py#L1199-L1201](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1199-L1201)): `self.n = n`, then `self.close()`. They sit in a `finally`, which is the real guarantee here — a `break`, an exception in the caller's body, a `return` out of the loop, all land in the same place. The terminal is left tidy whether or not the loop finished.

## Leaving the registry

`close` opens with a guard that doubles as a latch ([std.py#L1270-L1276](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1270-L1276)):

```python
if getattr(self, 'disable', True):
    return
self.disable = True
```

The `getattr` default of `True` is defensive: a bar that failed halfway through `__init__` has no `disable` attribute and is treated as already closed rather than crashing in a destructor. For this bar, `disable` was `False`, so the latch flips and everything after this point will happen exactly once.

`pos = abs(self.pos)` is read *before* deregistration, then `_decr_instances(self)` ([std.py#L1278-L1280](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1278-L1280)) takes the process-global lock — the same `TqdmDefaultWriteLock` from Chapter 1 — and removes the instance from the `WeakSet` ([std.py#L697-L703](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L697-L703)). The trace shows the removal machinery working: `tqdm.__hash__ → 4456456720`, which is just `id(self)` ([std.py#L1163-L1164](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1163-L1164)), followed by `Comparable.__eq__` ([utils.py#L108-L109](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L108-L109)) consulting `_comparable` twice and getting `0` both times ([std.py#L1159-L1161](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1159-L1161)). Hashing is by identity; equality is by screen position. A `KeyError` on removal is swallowed on purpose — a bar that has already vanished is not an error.

With the instance gone, `_decr_instances` looks for an unfixed bar that had been pushed past the visible rows (`pos >= nrows - 1`), clears it and moves it into the freed slot ([std.py#L705-L715](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L705-L715)). Here there are no other bars, so nothing moves. The docstring is candid about the trade: order is not maintained, flicker and blank space are.

## Three ways to print nothing

Before drawing, `close` has three escape hatches, none of which this bar takes.

If `last_print_t` was never set, or `last_print_t < start_t + delay` — the bar never displayed — it returns silently ([std.py#L1282-L1286](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1282-L1286)). A `delay=` long enough to outlive a fast loop therefore leaves *no trace at all*, which is the point of the option. If `self.sp` is `None` — a GUI subclass — it returns too ([std.py#L1289-L1290](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1289-L1290)).

The third is a live probe. `close` defines a bare `fp_write` and calls it with the empty string ([std.py#L1293-L1301](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1293-L1301)):

```
tqdm.close.<locals>.fp_write(s='')
  DisableOnWriteError.disable_on_exception.<locals>.inner() → 0
```

Zero characters written, no exception. Had the stream been closed underneath the bar, the `ValueError` containing `'closed'` would be caught and `close` would return — shutting down a bar whose terminal has gone away is not treated as a failure. Any other `ValueError` re-raises.

## The final frame tells a different story

`leave = pos == 0 if self.leave is None else self.leave` ([std.py#L1303](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1303)) resolves to `True`. Under the lock, two statements run that are easy to miss ([std.py#L1305-L1310](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1305-L1310)):

```python
self._ema_dt = lambda: None
self.display(pos=0)
```

The EMA that Chapter 8 spent two updates training is *thrown away* and replaced with a function that returns `None`. `format_dict` computes `rate` as `self._ema_dn() / self._ema_dt() if self._ema_dt() else None` ([std.py#L1466](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1466)) — the condition is evaluated first, is now falsy, and `_ema_dn()` is never even called. That is visible in the trace: at line 558 `format_dict` has no `EMA.__call__` beneath it at all, unlike every earlier render.

`format_meter` therefore receives `rate=None` with `elapsed=0.230072021484375`, and falls back to the plain overall average ([std.py#L550-L551](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L550-L551)): `(4 - 0) / 0.230072 = 17.386`, formatted `17.39it/s`. The bar renders at `frac=1.0`, ten solid blocks, 59 columns:

```
Processing d: 100%|██████████| 4/4 [00:00<00:00, 17.39it/s]
```

Note `17.39`, where the in-flight frame a moment earlier said `17.50`. The closing line deliberately reports a *different statistic* — the honest overall throughput for the whole run, not the smoothed recent speed. `display(pos=0)` also means the final frame is drawn at the top line rather than wherever the bar had been, and `display`'s own guards still apply: a position at or beyond `nrows` prints nothing ([std.py#L1484-L1492](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1484-L1492)), so closing a hidden nested bar cannot scribble on the wrong row. Then `fp_write('\n')` — one character — commits the line and the lock is released.

Had `leave` been `False`, the other branch would have run instead: `display(msg='', pos=pos)` to blank the line, plus a `'\r'` to park the cursor ([std.py#L1311-L1314](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1311-L1314)).

> **For the owner:** The rate on the final line is `n/elapsed`, not the exponential moving average shown while the bar was running, so the two numbers can legitimately differ. Do not treat the closing line as a continuation of the live rate series.

## Reading a dead bar

Back in the caller, the next statement is `stats = dict(pbar.format_dict)` — on a bar that is already closed. It works ([std.py#L1453-L1469](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1453-L1469)): the instance still has `unit`, so the normal branch runs and returns `{'n': 4, 'total': 4, 'elapsed': 0.23186588287353516, ...}` with `rate` now `None` for the same lambda reason. (A bar closed before `unit` was ever assigned would get the `defaultdict(lambda: None, ...)` branch instead, so absent keys read as `None` rather than raising ([std.py#L1456-L1458](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1456-L1458)).) This is how the scenario's `assert stats["n"] == stats["total"] == 4` is satisfied.

`format_dict` is documented as "public API for read-only member access", and mostly is — except that under `dynamic_ncols` it re-probes the terminal and writes `self.ncols` and `self.nrows` ([std.py#L1459-L1460](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1459-L1460)).

Then the caller's explicit `pbar.close()`. The latch holds: `disable` is `True`, so the method returns at its first line, printing nothing and touching no lock. Later, when the object is collected, `__del__` calls `close` once more ([std.py#L1153-L1154](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1153-L1154)) and again returns `None`. Three closes, one final frame.

> **For the owner:** Relying on `__del__` to close a bar makes the timing of the final frame depend on garbage collection; prefer `with tqdm(...) as t:`, whose `__exit__` closes deterministically and downgrades a late `AttributeError` to a `TqdmWarning` rather than raising during teardown ([std.py#L1144-L1151](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1144-L1151)).

The guarantees, in sum: the wrapped iterable is passed through unchanged; output goes to `stderr` and is throttled by `mininterval` and a self-tuning `miniters`; display and registry mutations happen under one process-global reentrant lock; stream and terminal failures degrade to a silent bar rather than an exception; and the bar is always closed, idempotently, from the iterator's `finally`. The risks worth naming before signing off: a shared daemon thread and a global lock held as class state, `TQDM_*` environment variables that can silently redefine defaults for every bar in the process, a display that lags the loop by design, and broad `except` clauses that hide I/O failures from the caller.

> **Leaves as:** `text == "abcd"` and `stats == {'n': 4, 'total': 4, 'elapsed': 0.23186588287353516, 'rate': None, ...}`; the bar deregistered, `disable=True`, and the last line on stderr `Processing d: 100%|██████████| 4/4 [00:00<00:00, 17.39it/s]\n`
