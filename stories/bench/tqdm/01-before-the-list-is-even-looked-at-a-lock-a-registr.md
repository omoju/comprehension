# Chapter 1 · Before the list is even looked at: a lock, a registry, a thread

> **Enters as:** `['a', 'b', 'c', 'd']`, passed to `tqdm(...)`

The list is four strings. It has no idea it is about to become the payload of a progress meter, and for the whole of this chapter it will be ignored.

That is literal. The call `tqdm(chars)` goes first to `tqdm.__new__`, whose signature is `def __new__(cls, *_, **__)` — the arguments are captured into throwaway names and never read ([std.py#L664-L665](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L664-L665)). The list sits on the stack while tqdm builds the world it is about to enter: a process-wide write lock, a registry of live bars, and a background thread.

## The lock, built on demand

The first thing `__new__` does is `with cls.get_lock():` ([std.py#L666](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L666)). `get_lock` is deliberately lazy: it constructs a `TqdmDefaultWriteLock` only if the class has no `_lock` yet ([std.py#L766-L771](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L766-L771)). In this run it does not exist, so the trace shows `TqdmDefaultWriteLock.__init__` being called once, and the object it returns — `<tqdm.std.TqdmDefaultWriteLock object at 0x109742a50>` — becomes class state for the rest of the process.

That lock is two locks in a trench coat. A threading `RLock` is created at import time as a class attribute ([std.py#L86](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L86)); a `multiprocessing.RLock` is created only now, on first use, by `create_mp_lock` ([std.py#L114-L121](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L114-L121)). The comment above the class attribute explains why the multiprocessing lock is not made at import: creating one fixes the multiprocessing start context, which would forbid `spawn()` and `forkserver()` in the host application ([std.py#L83-L86](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L83-L86)). The two are stored in a list, acquired in order and released in reverse ([std.py#L96-L106](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L96-L106)).

## The registry, entered before configuration

Inside that lock, the freshly allocated instance is added to `cls._instances` — a `WeakSet` held on the class ([std.py#L365](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L365), [std.py#L667](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L667)). The trace records `tqdm.__hash__` returning `4453575920`, which is simply `id(self)` ([std.py#L1163-L1164](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1163-L1164)) — the set keys bars by identity.

Note the ordering: the instance joins the global registry before a single argument has been validated. That is why `__init__` has to undo it by hand on the two paths where no bar will be drawn — `disable=True` removes itself from `_instances` and returns ([std.py#L990-L999](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L990-L999)), and an unknown keyword argument removes itself and *then* raises ([std.py#L1001-L1012](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1001-L1012)).

## The thread

Still under the lock, `__new__` checks `cls.monitor_interval` (10 by default) and whether a monitor is already alive, then constructs `TMonitor(cls, 10)` ([std.py#L669-L672](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L669-L672)). The trace shows exactly that: `TMonitor.__init__(tqdm_cls=<class 'tqdm.std.tqdm'>, sleep_interval=10)`.

The thread names itself `tqdm_monitor`, marks itself `daemon` so a `KeyboardInterrupt` in the main thread kills it, registers an `atexit` handler, and starts ([_monitor.py#L31-L40](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L31-L40)). That handler only *sets* a kill event — it never joins — precisely to avoid deadlocking at interpreter exit on a dead fork or a stuck thread ([_monitor.py#L42-L48](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L42-L48)).

Its job, once per `sleep_interval`, is narrow: take the same global write lock, look at registered bars whose `miniters > 1` and whose last print is older than `maxinterval`, force `miniters = 1` and repaint them ([_monitor.py#L75-L93](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L75-L93)). It deliberately skips instances that have no `start_t` yet ([_monitor.py#L56-L60](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L56-L60)) — which is why our instance, at this moment, is invisible to it.

> **For the owner:** Constructing any `tqdm` bar creates process-global state — a reentrant write lock and one daemon thread — before any argument is checked, including for bars that will immediately be disabled. Set `tqdm.tqdm.monitor_interval = 0` before the first bar if an extra daemon thread is unacceptable in your environment.

If `TMonitor(...)` had raised, the caller would never hear about it: the exception is caught, a `TqdmMonitorWarning` is emitted, and `monitor_interval` is set to `0`, disabling monitoring for the whole process from then on ([std.py#L673-L677](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L673-L677)).

> **For the owner:** A failure to start the monitor degrades silently and permanently, so the `maxinterval` safety net ("a stalled bar will be repainted within 10 seconds") is a best-effort guarantee, not a hard one. Treat `TqdmMonitorWarning` as a signal that bars may freeze on screen during slow iterations.

The lock is released ([std.py#L111-L113](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L111-L113)) and `__new__` returns `<tqdm.std.tqdm object at 0x109742cf0>` — an object with no `iterable`, no `n`, no `total`, no `start_t`. The list has not been touched. It is about to be.

> **Leaves as:** `['a', 'b', 'c', 'd']`, still untouched, now about to be handed to `tqdm.__init__` on `<tqdm.std.tqdm object at 0x109742cf0>` — an instance already in `tqdm._instances`, with a process-global `TqdmDefaultWriteLock` and a live daemon `TMonitor` behind it
