# Chapter 8 · The gates open: update(2), the EMA rate, self-tuned miniters, and the run to 100%

> **Enters as:** the bar at `0x109a02210` with `n=0`, `last_print_n=0`, `desc='Processing b: '`, `miniters=0`, both EMAs empty; the generator's private `n` at 1, resuming for the third item

The caller's loop body has finished with `'b'`. The generator wakes up at the same four lines that declined to do anything last time:

```python
n += 1

if n - last_print_n >= self.miniters:
    cur_t = time()
    dt = cur_t - last_print_t
    if dt >= mininterval and cur_t >= min_start_t:
        self.update(n - last_print_n)
```

([std.py#L1190-L1196](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1190-L1196)). Private `n` becomes 2. The counter gate opens as before. This time `dt` is about 0.110 s — the two sleeps since the last publication — and `mininterval` is 0.1. Both gates agree, and for the first time in this bar's life the trace shows something underneath `__iter__`: `tqdm.update(self=<tqdm>, n=2)`.

Note the argument. Not `1` per item: `n - last_print_n`, the whole backlog at once. The two items that were consumed in silence are published together.

## Inside `update`: gates again, then the averages

`update` does not trust its caller. It re-runs the same two gates on its own state ([std.py#L1237-L1240](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1237-L1240)), because it is also the public API — the method a caller uses directly when driving a bar by hand. (A negative `n` is tolerated: `last_print_n` is decremented to match so the auto-refresh arithmetic still works on a meter that goes backwards ([std.py#L1232-L1233](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1232-L1233)). On a disabled bar the whole method is a `return` ([std.py#L1229-L1230](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1229-L1230)).)

`self.n` becomes 2. The cheap counter check comes first *specifically* to avoid calling `time()` on every iteration — that is the comment on the line ([std.py#L1236-L1238](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1236-L1238)). Then `dn = 2`, and with `smoothing` truthy and both `dt` and `dn` non-zero, the two accumulators are finally fed ([std.py#L1243-L1246](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1243-L1246)):

```
EMA.__call__(self=<EMA>, x=2) → 1.9999999999999996
```

That is `_ema_dn`. Its arithmetic is `last = alpha*x + beta*last`, returned de-biased by `1 - beta**calls` ([std.py#L235-L239](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L235-L239)) — the division is what makes a *first* sample report itself rather than three-tenths of itself, and the floating-point residue 1.9999999999999996 is the visible trace of it. `_ema_dt` takes the interval the same way.

Then `refresh(lock_args=self.lock_args)`, and the render chain runs as in Chapter 7 — except that `format_dict` now finds a non-zero `_ema_dt()` (0.11034297943115233) and so computes a real rate instead of `None` ([std.py#L1466](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1466)):

```
rate = 1.9999999999999996 / 0.11034297943115233 = 18.125303578991037
```

This is an *exponential moving average* of increments over intervals, not `n/elapsed`. Recent intervals dominate; `smoothing=0.3` is the dial. With a rate in hand, `format_meter` stops printing `'?'`: `inv_rate` is 0.055, less than 1, so the non-inverted form wins and `rate_fmt` becomes `'18.13it/s'` ([std.py#L552-L559](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L552-L559)), and `remaining = (4 - 2)/18.125` formats as `'00:00'` ([std.py#L573-L574](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L573-L574)). `Bar` is built at `frac=0.5`; `divmod(int(0.5 * 10 * 8), 8)` gives five whole blocks and no partial, padded to ten cells ([std.py#L202-L207](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L202-L207)):

```
Processing b:  50%|█████     | 2/4 [00:00<00:00, 18.13it/s]
```

59 columns by `disp_len`, 60 characters written. The counter has jumped from 0 to 2 in one step.

> **For the owner:** tqdm guarantees it will not spam the terminal faster than `mininterval`; it does not guarantee any particular number of intermediate frames, and a short or fast loop may show only its first and last. Do not build logging or monitoring that assumes a frame per iteration.

## The bar rewrites its own throttle

Back in `update`, after the print, `dynamic_miniters` takes over ([std.py#L1248-L1263](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1248-L1263)). `dt` (0.110) is well under `maxinterval` (10), so the smoothed branch runs:

```
EMA.__call__(self=<EMA>, x=1.8125303578991039) → 1.8125303578991034
```

`miniters` is now 1.8125 — a float, which is fine because the gate is a `>=` comparison, not an index. The bar has just decided, from observed speed, that roughly 1.8 items fit into a `mininterval`, and it will skip the clock entirely until that many have accumulated. `last_print_n` and `last_print_t` are stored, and `update` returns `True` — its documented signal that a display actually happened ([std.py#L1226-L1228](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1226-L1228), [std.py#L1266-L1268](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1266-L1268)).

> **For the owner:** `update()` returns `True` only when a frame was drawn, which is the supported hook for custom callbacks that want tqdm's throttling rather than their own; everything else returns `None`. Point integrators at that return value instead of having them re-implement rate limiting.

Item `'c'` is yielded. The caller sleeps and calls `set_description("Processing c")`, which — as Chapter 7 established — bypasses both gates and repaints immediately ([std.py#L1399-L1401](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1399-L1401)). The EMAs have not been touched, so `format_dict` reports the same `rate=18.125303578991037`, and `elapsed` has crept to 0.1675:

```
Processing c:  50%|█████     | 2/4 [00:00<00:00, 18.13it/s]
```

The generator resumes: private `n` becomes 3, and `3 - 2 = 1` is *not* `>= 1.8125`. The counter gate is shut, so `time()` is never called at all — the cheap check doing exactly its job. `'d'` is yielded, `set_description("Processing d")` forces another identical repaint at `elapsed=0.2253`, still `2/4`, still `18.13it/s`.

> **For the owner:** The rate on screen is the rate as of the last counter publication, not an instantaneous measurement — three consecutive frames here report `18.13it/s` while no new timing sample exists. Also note that `dynamic_miniters` can leave `miniters` large after a burst of fast iterations, freezing the bar if the loop then slows; the recovery is the monitor thread, which forces `miniters = 1` and a refresh once `maxinterval` is exceeded ([_monitor.py#L85-L93](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L85-L93)). Setting `tqdm.monitor_interval = 0` removes that rescue.

## Four of four

The last resumption: private `n` becomes 4, `4 - 2 = 2 >= 1.8125`, `dt ≈ 0.117 >= 0.1`. `update(2)` again. `self.n` becomes 4; `_ema_dn(2)` returns exactly `2.0` this time, `_ema_dt` settles at `0.1142889471615062`, and the rate is `17.499504979897324` — the second interval was slightly longer, and the average bent toward it.

`format_meter` first checks whether the total is still meaningful: `n >= total + 0.5` would discard it and fall back to a counter-only line ([std.py#L533-L536](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L533-L536)). `4 >= 4.5` is false, so `total=4` survives and `frac` is exactly 1.0. `Bar` computes `divmod(80, 8) = (10, 0)`; `bar_length` is not less than `N_BARS`, so no padding is appended and the bar is ten solid blocks ([std.py#L205-L207](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L205-L207)):

```
Processing d: 100%|██████████| 4/4 [00:00<00:00, 17.50it/s]
```

59 columns, 60 characters, written under the global lock like every other frame. Then `miniters` is retuned one last time, `EMA(1.7086550917816143) → 1.7514272601829333`, `last_print_n` becomes 4, and `update` returns `True`.

The list is empty. The generator's `for` loop is about to raise `StopIteration` into its `finally`.

> **Leaves as:** the bar with `n=4`, `last_print_n=4`, `miniters=1.7514272601829333`, EMAs at `dn=2.0` and `dt=0.1142889471615062`, the screen showing `Processing d: 100%|██████████| 4/4 [00:00<00:00, 17.50it/s]`, and `update` having returned `True` to an iterator one step from its `finally`
