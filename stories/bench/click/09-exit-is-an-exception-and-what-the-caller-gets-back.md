# Chapter 9 · Exit is an exception, and what the caller gets back

> **Enters as:** the callback's return value `None`, handed back to `main`, with the context still open at `_depth == 1`

## The return value is deliberately thrown away

`rv` is `None`. `main` does not look at it. In standalone mode it falls straight to [`ctx.exit()`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L1587-L1598), and the comment sitting above that line is the whole argument: it is not safe to call `ctx.exit(rv)`, because `rv` may be `1` — which looks like success to a Python author and like failure to a shell — and because a chained group returning `[None, None]` has no meaningful truthiness at all. So success is one fixed thing: exit code 0, chosen by Click, not inferred from your function.

> **For the owner:** Returning a value from a command callback has no effect on the process exit code. If a command must fail, call `ctx.exit(n)` or raise a `ClickException`; a `return 1` will exit 0 and look like success to CI.

## Closing before raising

[`Context.exit`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L845-L853) does two things in order. It calls [`close()`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L715-L721), which forwards to [`_close_with_exception_info(None, None, None)`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L722-L738) and unwinds the `ExitStack` that has been riding along since chapter 3 — every `call_on_close` callback, every `with_resource` context manager. Nothing is registered here, so it returns `False`. A fresh `ExitStack` is installed in its place, so the context survives reuse.

Only then does it raise [`Exit(0)`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/exceptions.py#L366-L378) — a bare `RuntimeError` subclass carrying one integer. The ordering is the guarantee: an early exit still runs your cleanup. A `click.File` parameter opened during parsing gets flushed and closed before the process goes away, not after.

The `Exit` travels up through `main`'s `with self.make_context(...) as ctx` block, so [`Context.__exit__`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L580-L592) runs with the live `(Exit, Exit(0), <traceback>)` triple. `_depth` drops to 0, so `_close_with_exception_info` is called a second time — on the new, empty stack, returning `False` again — and this time the exception information is forwarded into `ExitStack.__exit__`. That is not decoration: a registered resource can inspect the failure that is tearing the context down, and can suppress it by returning true. Then [`pop_context()`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/globals.py#L49-L51) removes the context from the thread-local stack, and `__exit__` returns `False`, letting the `Exit` keep going.

## The ladder, and the road not taken

[`except Exit`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L1599-L1611) copies `e.exit_code` into the local `exit_code`, leaves `report` as `None`, and the teardown after the `try` [writes nothing and calls `sys.exit(0)`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L1637-L1640).

Had `--count=x` arrived instead, the `BadParameter` raised back in chapter 7 would have been caught by [`except ClickException`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L1625-L1629), which sets `report, exit_code = e.show, e.exit_code` — 2 for a `UsageError`. [`UsageError.show`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/exceptions.py#L87-L111) then prints the usage line, a hint built from the *longest* help name (`Try 'hello --help' for help.`), and `Error: Invalid value for '--count': 'x' is not a valid integer.` — all to stderr. A `Ctrl-C` or exhausted stdin would have gone through [the `EOFError`/`KeyboardInterrupt` arm](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L1617-L1624) to `Aborted!` and the initial `exit_code = 1`.

One policy is worth naming because it is a conscious trade. The whole ladder, *including* the reporting step, sits inside [an outer `except (EOFError, KeyboardInterrupt)`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/core.py#L1641-L1645) that simply calls `sys.exit(exit_code)`. If a user interrupts while the error message is being written, the message may be lost — the intended exit code still wins.

## What the runner makes of a `SystemExit`

`sys.exit(0)` raises `SystemExit`, which the runner catches in [its own handler](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L688-L703). `e.code` is `0`, so it is not `None` and not non-zero: `exception` stays `None`, `exit_code` becomes `0`, and `exc_info` keeps the `(SystemExit, SystemExit(0), traceback)` triple for anyone who wants it. A non-integer code would have been written to stdout and coerced to `1`.

Separately, [`except Exception`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L705-L710) swallows a genuine crash into `exit_code = 1` plus `result.exception`, because `catch_exceptions` defaults to `True`.

> **For the owner:** A test that asserts only on `result.output` will pass while the command crashed, because the exception is captured rather than raised. Assert `result.exit_code == 0` (or pass `catch_exceptions=False`) in every test that is meant to prove a command works.

The [`finally`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L711-L728) flushes both streams — two more `BytesIOCopy.flush` calls — and, in `fd` mode, stops the `_FDCapture`s and merges their bytes into the same buffers so late or C-level writes are not lost. Here `capture='sys'`, so it goes straight to `getvalue()` on all three buffers: `b'Your name: Click\nHello, Click!\nHello, Click!\nHello, Click!\n'` for stdout and for the mixed output, `b''` for stderr.

Leaving the `with self.isolation(...)` block runs [isolation's own `finally`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L576-L594): `os.environ` keys restored (including deleting ones that were absent), `sys.stdout/stderr/stdin` put back, the two `termui` prompt hooks and `_getchar` restored, both references to `should_strip_ansi` restored, `FORCED_WIDTH` restored, `pdb.Pdb.__init__` unpatched. Unconditionally, whatever happened inside. As the old wrappers lose their last reference, their `close` runs — and [that method is an empty no-op by design](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L184-L190), because the `BytesIO` underneath belongs to the `StreamMixer` and the `Result` is about to read it.

[`Result`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L262-L280) is a plain record of those bytes. [`result.output`](https://github.com/pallets/click/blob/06b2a678741131fd577ce170e23e5ca0aeba0309/src/click/testing.py#L282-L292) decodes with `errors='replace'` and normalises `\r\n`, so undecodable output never raises at assertion time — and the string the scenario prints is `'Your name: Click\nHello, Click!\nHello, Click!\nHello, Click!\n'`, exactly what a user at a terminal would have seen.

> **Leaves as:** `Result(exit_code=0, exception=None, exc_info=(SystemExit, SystemExit(0), tb), stdout_bytes=b'Your name: Click\nHello, Click!\nHello, Click!\nHello, Click!\n', stderr_bytes=b'')`, and `result.output` as the matching `str`
