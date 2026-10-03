# Chapter 2 · Accepting the arguments: a wrapped stderr, a borrowed `len`, and a guess about Unicode

> **Enters as:** `['a', 'b', 'c', 'd']`, passed as `iterable` to `tqdm.__init__` on `<tqdm.std.tqdm object at 0x109742cf0>`

Now the list is looked at. `__init__` receives it alongside a long tail of defaults the caller never typed: `desc=None, total=None, leave=True, file=None, ncols=None, mininterval=0.1, maxinterval=10.0, miniters=None, ascii=None, disable=False, unit='it', unit_scale=False, smoothing=0.3, unit_divisor=1000, delay=0.0, gui=False` — exactly as the trace records them.

Those defaults did not come straight from the `def` line. `__init__` is wrapped by `envwrap("tqdm", is_method=True, ...)` ([std.py#L958-L959](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L958-L959)), which scans `os.environ` at import time for keys beginning `TQDM_`, keeps those matching a parameter name, coerces them to the type of the parameter's default, and binds them as a `partialmethod` ([utils.py#L44-L75](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L44-L75)). In this run no such variables are set, so the defaults stand.

> **For the owner:** Any `TQDM_*` environment variable matching a parameter name silently changes the defaults for every bar in the process — `TQDM_MININTERVAL=5` and `TQDM_DISABLE=1` are the documented examples. Check your deployment environment before concluding that a bar's observed behaviour comes from the code you reviewed.

## The stream it will write to

`file` is `None`, so it becomes `sys.stderr` ([std.py#L968-L969](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L968-L969)). That default matters for the scenario's shape: a bar on `stderr` never contaminates a pipeline's `stdout`, which is what makes `cat *.txt | tqdm | wc -l` work at all.

`write_bytes` is false, so the `SimpleTextIOWrapper` branch is skipped and the stream goes straight into `DisableOnWriteError(file, tqdm_instance=self)` ([std.py#L971-L977](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L971-L977)). The trace shows what that constructor does: `ObjectWrapper.__init__` stashes the real `TextIOWrapper` as `_wrapped`, then `disable_on_exception` is called twice — once for `write`, once for `flush` — each returning an `inner` closure that is set as an attribute on the wrapper itself ([utils.py#L196-L203](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L196-L203)).

What `inner` does is the first real risk decision in this chapter. It calls the wrapped method, and if that raises `OSError` with `errno == 5` (I/O error) or a `ValueError` whose message contains `'closed'`, it swallows the exception and instead sets `miniters = float('inf')` on a weak proxy to the bar ([utils.py#L170-L194](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L170-L194)). An infinite `miniters` means the counter gate in `update` can never open again, so the bar goes quiet. Any other `OSError` or `ValueError` is re-raised.

> **For the owner:** If the output stream breaks mid-loop — closed file, detached terminal, `errno 5` — the bar silently stops updating and the caller's loop continues with no exception and no log line. This is deliberate (a progress meter should not kill the work it measures), but it means the absence of a bar is not evidence that the loop finished.

A `proxy` is used rather than a strong reference ([utils.py#L175](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L175)) so the wrapper does not keep a dead bar alive; the `ReferenceError` that follows a collected bar is caught and ignored.

`disable` is `False`, not `None`, so the `isatty` check at [std.py#L979-L980](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L979-L980) does not fire. Had the caller passed `disable=None`, a non-TTY stderr would have turned the bar off entirely.

## Borrowing a `len`

Here the list finally earns its keep. `total` is `None` and `iterable` is not, so:

```python
try:
    total = len(iterable)
except (TypeError, AttributeError):
    total = None
```

([std.py#L982-L988](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L982-L988)). Four items, so `total = 4`. The same lines are why wrapping a generator does not raise: the `TypeError` is caught and the bar degrades to counter-only output with no percentage and no ETA. An explicit `total=float("inf")` is normalised to `None` on the next line, treated as "unknown" rather than as a number to divide by.

With `disable` false and `kwargs` empty, neither of the two early-exit paths from Chapter 1's registry discussion runs: the instance stays in `_instances` and the method continues.

## Two probes at the terminal

Because `ncols` and `nrows` are both `None` and `file` compares equal to `sys.stderr`, the preprocessing block at [std.py#L1015-L1029](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1015-L1029) runs. That `in (sys.stderr, sys.stdout)` test is why the trace shows `DisableOnWriteError.__eq__` returning `True`: the wrapper forwards equality to its `_wrapped` object so it still *is* stderr for comparison purposes ([utils.py#L205-L206](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L205-L206)).

`dynamic_ncols` is false, so the `else` branch builds a one-shot probe: `_screen_shape_wrapper()` returns an `inner` that calls `os.get_terminal_size(fp.fileno())` inside a bare `except Exception: return None, None` ([utils.py#L265-L278](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L265-L278)). The trace shows `ObjectWrapper.__getattr__` fetching `fileno` through the wrapper ([utils.py#L121-L123](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L121-L123)) and the result being `(None, None)` — this run's stderr is not an interactive terminal. So `ncols` and `nrows` both stay `None`.

That is a consequential `None`. With no `ncols`, nothing downstream will trim the rendered line to the console width; the bar will be a fixed ten cells and the line printed in full. With no `nrows`, the visibility checks in `display` and `clear` will fall back to a hard-coded 20 rows.

> **For the owner:** Terminal geometry detection swallows every exception and falls back to "unknown", which disables width-based trimming rather than failing. If a bar's description is long and the console narrow, the line wraps and the `\r` in-place update produces one line per refresh — the most common cosmetic complaint about tqdm. Pass `ncols=` explicitly where output width is predictable.

## Guessing at Unicode

`ascii` arrived as `None`, so `ascii = not _supports_unicode(file)` ([std.py#L1043-L1044](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1043-L1044)). `_supports_unicode` reads `fp.encoding` — again through the wrapper's `__getattr__`, yielding `'utf-8'` — and hands it to `_is_utf`, which tries to encode two block characters and returns `True` on success ([utils.py#L235-L253](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/utils.py#L235-L253)). So `ascii = False`: this bar will draw with smooth Unicode blocks. A stream with no `encoding` attribute raises `AttributeError`, which `_supports_unicode` catches and converts to `False`, degrading the bar to `" 123456789#"`.

`mininterval` (0.1), `maxinterval` (10.0) and `smoothing` (0.3) are all non-`None`, so the three "coerce `None` to 0" guards at [std.py#L1037-L1051](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1037-L1051) pass through unchanged. `miniters` *is* `None`, which sets `miniters = 0` and `dynamic_miniters = True` ([std.py#L1031-L1035](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1031-L1035)) — tqdm has just granted itself permission to rewrite its own display-frequency threshold as the loop runs. That decision will bite in Chapter 8.

## Three accumulators

The arguments are stored onto `self` ([std.py#L1053-L1082](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1053-L1082)), and along the way three `EMA(0.3)` objects are constructed — the trace shows `EMA.__init__` once plus "×2 more". They track, respectively, the increment per print, the interval per print, and the tuned `miniters` ([std.py#L1076-L1078](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1076-L1078)). Each starts with `last = 0` and `calls = 0` ([std.py#L223-L226](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L223-L226)), which is why the first rendered frame will report a rate of `?`.

`postfix` is `None`, so the `set_postfix` branch at [std.py#L1083-L1087](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1083-L1087) is skipped, and `self.postfix` stays `None`.

The list is now `self.iterable`, its length is `self.total = 4`, and the object knows where and how it will draw. What it does not yet have is a line to draw on.

> **Leaves as:** the same four strings, now `self.iterable` on a bar with `total=4`, `fp=<DisableOnWriteError>` over stderr, `ncols=None`, `nrows=None`, `ascii=False`, `miniters=0`, `dynamic_miniters=True`, and three fresh `EMA(0.3)` accumulators — about to acquire a screen position
