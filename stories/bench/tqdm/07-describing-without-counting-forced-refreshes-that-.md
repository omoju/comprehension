# Chapter 7 · Describing without counting: forced refreshes that show stale progress

> **Enters as:** the bar at `0x109a02210` with `n=0`, `last_print_n=0`, `desc='Processing'`, `total=4`, `miniters=0`, `mininterval=0.1`, and the caller entering `for char in pbar:`

The list has been a passenger for two chapters. Now it starts giving up its contents, one at a time, and the first thing to say about `__iter__` is what it does *not* do to them:

```python
for obj in iterable:
    yield obj
```

([std.py#L1186-L1187](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1186-L1187)). The trace agrees: `tqdm.__iter__(self=<tqdm>) → 'a'`. The same string object the caller put in comes back out. Everything tqdm does around that line is bookkeeping; the sequence itself is untouched.

Before the loop begins, `__iter__` copies the instance's state into locals — `mininterval`, `last_print_t`, `last_print_n`, `min_start_t`, and crucially `n = self.n` ([std.py#L1178-L1183](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1178-L1183)). From here on there are two counters: the generator's private `n`, which advances on every item, and `self.n`, which the display reads. They are not the same number, and this chapter is the gap between them.

## `set_description` mutates, then insists on painting

With `'a'` in hand the caller sleeps 50 ms and calls `pbar.set_description("Processing a")`. That method is two lines of work:

```python
self.desc = desc + ': ' if desc else ''
if refresh:
    self.refresh()
```

([std.py#L1399-L1401](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1399-L1401)). `desc` becomes `'Processing a: '` — the colon and space are appended here, which is why `format_meter`'s `prefix[-2:] == ": "` check exists at the other end and declines to add a second one ([std.py#L582-L587](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L582-L587)). (`set_description_str` is the variant that stores the string verbatim ([std.py#L1403-L1407](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1403-L1407)).)

Then `refresh()`. Not "refresh if enough time has passed" — `refresh` takes the global write lock, calls `display()`, and releases ([std.py#L1345-L1357](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1345-L1357)). There is no consultation of `mininterval` or `miniters` anywhere on this path. The throttling machinery that Chapter 4 described lives entirely inside `update`; `set_description` goes around it.

So the full render runs: `display` → `__str__` → `format_meter(**self.format_dict)` ([std.py#L1156-L1157](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1156-L1157)). The snapshot `format_dict` hands over is the one the trace records:

```
{'n': 0, 'total': 4, 'elapsed': 0.05352497100830078, 'prefix': 'Processing a: ', 'rate': None, ...}
```

Two fields deserve attention. `elapsed` is computed live, `self._time() - self.start_t` ([std.py#L1463](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1463)), so the clock is honest: 53 ms have really passed. `rate` is `self._ema_dn() / self._ema_dt() if self._ema_dt() else None` ([std.py#L1466](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1466)) — and the trace shows `EMA.__call__(x=None) → 0`, because no `update` has ever fed it an interval. `rate` is therefore `None`, and `format_meter` falls through to the `'?'` placeholders for speed and remaining time rather than dividing by zero ([std.py#L550-L559](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L550-L559), [std.py#L573-L574](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L573-L574)).

And `n` is `0`. The item `'a'` has been consumed, the caller has already done its work with it, but `self.n` has not moved, because nothing has called `update`. `Bar` is constructed at `frac=0.0` and renders ten spaces ([std.py#L202-L208](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L202-L208)). The line that reaches the terminal is:

```
Processing a:   0%|          | 0/4 [00:00<?, ?it/s]
```

`disp_len` measures it at 51 columns — ANSI stripped, wide characters counted double ([utils.py#L307-L312](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L307-L312)) — and `print_status` writes `'\r' + s` with no padding, since 51 exceeds the previous 49 ([std.py#L453-L459](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L453-L459)). 52 characters go out through the error-swallowing wrapper.

> **For the owner:** `set_description(..., refresh=True)` is the default and forces a full render plus a stream write on every call, ignoring `mininterval` and `miniters` entirely. In a loop that calls it per iteration this converts tqdm's throttled output into one frame per item. Pass `refresh=False` in hot loops and let the next `update` repaint.

## The gate check that printed nothing

The caller's loop body ends and the generator resumes. This is where the throttling actually lives:

```python
n += 1

if n - last_print_n >= self.miniters:
    cur_t = time()
    dt = cur_t - last_print_t
    if dt >= mininterval and cur_t >= min_start_t:
        self.update(n - last_print_n)
```

([std.py#L1190-L1196](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1190-L1196)). The private `n` becomes 1. The counter gate opens immediately — `1 - 0 >= 0`, since `miniters` is still the 0 that `dynamic_miniters` started it at. But `dt` is about 0.053 s and `mininterval` is 0.1, so the time gate stays shut and `update` is never called. The comment two lines above explains why this is inlined at all rather than calling `self.update(1)`: *does not call self.update(1) for speed optimisation* ([std.py#L1188-L1189](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1188-L1189)).

The trace shows this resumption only as its outcome — `tqdm.__iter__(self=<tqdm>) → 'b'`, with no `update` beneath it. `'b'` goes to the caller untouched; `self.n` is still 0.

The body repeats: sleep, `set_description("Processing b")`. `desc` becomes `'Processing b: '`, `refresh` fires again, and `format_dict` now reports `elapsed=0.10843706130981445` — the clock has moved — while `n` is still `0` and `rate` is still `None`. The frame is:

```
Processing b:   0%|          | 0/4 [00:00<?, ?it/s]
```

51 columns again, 52 characters written. Two of the four items are gone and the meter has not budged off zero.

> **For the owner:** The number on the bar is the last value `update` published, not the number of items the caller has consumed; `format_dict['n']` reports the same lagged value. Treat the display and `format_dict` as a monitoring view, not as a count you can act on. If a caller needs an exact consumed count, have them maintain it themselves or drive the bar manually with `update`.

Nothing here is a malfunction. The design is that cheap state changes (a description) may repaint freely, while the expensive, semantically meaningful counter advances only when both gates agree. The cost is a window — here two items wide — in which the terminal is confidently displaying a number that is out of date, with a live elapsed time beside it making the frame look fresher than it is.

> **Leaves as:** the same bar with `n=0`, `last_print_n=0`, `desc='Processing b: '`, both EMAs still at zero and `rate` still `None`; two items (`'a'`, `'b'`) consumed by the caller, the generator's private `n` at 1, and the last line on screen reading `Processing b:   0%|          | 0/4 [00:00<?, ?it/s]`
