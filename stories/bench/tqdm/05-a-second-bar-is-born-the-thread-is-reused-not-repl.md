# Chapter 5 · A second bar is born: the thread is reused, not replaced

> **Enters as:** the same four-item list, handed a second time — `tqdm(chars, desc="Processing")` — which Python routes first to `tqdm.__new__(cls=<type>)`

The list makes the same entrance it made in Chapter 1, and gets the same treatment: `__new__` does not look at it. Its signature is `def __new__(cls, *_, **__)` — the arguments are swallowed into throwaway names ([std.py#L664-L665](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L664-L665)). What happens in this span is entirely about class-level state that outlived the first bar.

## The lock is the same object

```python
with cls.get_lock():  # also constructs lock if non-existent
    cls._instances.add(instance)
```

([std.py#L666-L667](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L666-L667)). `get_lock` is guarded by a single `hasattr` check: `if not hasattr(cls, '_lock'): cls._lock = TqdmDefaultWriteLock()` ([std.py#L766-L771](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L766-L771)). Chapter 1 set `_lock`, so this time the constructor does not run — and the trace proves it: the call returns `<tqdm.std.TqdmDefaultWriteLock object at 0x109742a50>`, the identical address from line 8, with no nested `__init__` or `create_mp_lock` beneath it.

That one object is the serialisation point for every bar in the process, and for `tqdm.write` and `external_write_mode` too ([std.py#L717-L759](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L717-L759)). It is reentrant on both halves — a threading `RLock` and a multiprocessing `RLock`, acquired in order and released in reverse ([std.py#L96-L106](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L96-L106)) — which is what lets `close()` later take it while already inside locked code without deadlocking.

Inside that lock the new instance joins the registry. `_instances` is a `WeakSet` ([std.py#L365](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L365)), and the `tqdm.__hash__` call the trace records at this point — returning `4456456720`, the instance's own `id` ([std.py#L1163-L1164](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L1163-L1164)) — is the set computing its bucket. Identity, not position, decides membership here; position only enters later, through `Comparable.__eq__`.

## The monitor answers that it is still alive

Then the branch that makes this chapter:

```python
if cls.monitor_interval and (cls.monitor is None
                             or not cls.monitor.report()):
```

([std.py#L669-L670](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L669-L670)). `monitor_interval` is still `10`, so the first operand is truthy; `cls.monitor` is no longer `None`, so the question falls to `report()`:

```python
def report(self):
    return not self.was_killed.is_set()
```

([_monitor.py#L103-L104](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L103-L104)). The trace shows it returning `True`. The condition is therefore `10 and (False or False)` — false — and no new `TMonitor` is constructed. One daemon thread serves the whole process, surviving bars being created and closed. Note what was *not* checked: `report()` consults the kill event, not `is_alive()`. A monitor thread that died without setting the event would still report `True` and would not be replaced (inference from the two lines above; nothing in the trace exercises that case).

Had a monitor been needed and its construction raised, the failure would not reach the caller:

```python
except Exception as e:  # pragma: nocover
    warn("tqdm:disabling monitor support"
         " (monitor_interval = 0) due to:\n" + str(e),
         TqdmMonitorWarning, stacklevel=2)
    cls.monitor_interval = 0
```

([std.py#L673-L677](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/std.py#L673-L677)). A warning is emitted and monitoring is switched off for the rest of the process — the bar is delivered regardless.

## What the shared thread is allowed to do to your bar

The thread this list's bar is now registered with is not passive. Every `sleep_interval` seconds it wakes, takes the same global write lock, and walks the instances that have a `start_t` — the half-built ones are skipped on purpose ([_monitor.py#L56-L60](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L56-L60), and recall Chapter 3's deliberate ordering). For each one:

```python
if (
    instance.miniters > 1
    and (cur_t - instance.last_print_t) >= instance.maxinterval
):
    instance.miniters = 1
    instance.refresh(nolock=True)
```

([_monitor.py#L85-L93](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L85-L93)). That is the rescue for the hazard Chapter 8 will show being created: a bar whose self-tuned `miniters` grew large during fast iterations and then stalled when the loop slowed. The monitor forces `miniters` back to 1 and repaints from its own thread — holding the lock, which is why `refresh` is called with `nolock=True`. It re-checks the kill event inside the loop to keep shutdown prompt ([_monitor.py#L80-L82](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L80-L82)), and warns with `TqdmSynchronisationWarning` if the instance set changed under it ([_monitor.py#L96-L99](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L96-L99)).

> **For the owner:** A tqdm bar means a shared daemon thread that mutates your bar's `miniters` and writes to your output stream on its own schedule. It is created at the first bar and lives until exit. Set `tqdm.tqdm.monitor_interval = 0` before any bar is constructed if an extra thread is unacceptable in your environment; accept that bars with long stalls will then stop refreshing until the loop itself calls `update`.

Shutdown was arranged back in Chapter 1 and is worth stating here, because it is where a thread like this usually goes wrong. The thread is `daemon` ([_monitor.py#L33](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L33)), and the `atexit` hook only sets the event — it deliberately does not join:

```python
def _atexit_signal(self):
    """
    Non-joining shutdown signal.
    ...
    """
    self.was_killed.set()
```

([_monitor.py#L42-L48](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L42-L48)). The joining variant exists as `exit()`, which also refuses to join itself ([_monitor.py#L50-L54](https://github.com/tqdm/tqdm/blob/9cf5a12b1f955468a17f0ba3c59092b23e4258ac/tqdm/_monitor.py#L50-L54)). The net guarantee: interpreter exit cannot block on tqdm's monitor.

> **For the owner:** The lock and the monitor are class attributes on `tqdm.std.tqdm`, so they are shared by every subclass and every library in the process that imports tqdm. Check that nothing in your dependency tree reassigns `tqdm.set_lock(...)` or `monitor_interval` behind your back, because those choices are process-wide, not per-bar.

`__new__` releases the lock and returns `<tqdm.std.tqdm object at 0x109a02210>`: a bare object with no `iterable`, no `desc`, no `pos` — just a place in the registry and a claim on shared machinery. The list is still waiting outside.

> **Leaves as:** `<tqdm.std.tqdm object at 0x109a02210>` — a bare, registered instance sharing the one `TqdmDefaultWriteLock` at `0x109742a50` and the one live `TMonitor` (`report() → True`, no second thread started) — about to be handed the list and `desc='Processing'` by `__init__`
