"""Replays the scenario's first call up to the end of `tqdm.__new__`."""
from tqdm import tqdm
from tqdm._monitor import TMonitor
from tqdm.std import TqdmDefaultWriteLock

chars = ["a", "b", "c", "d"]

# --- the world before the list arrives ---------------------------------
assert not hasattr(tqdm, "_lock"), "lock must not exist before first bar"
assert tqdm.monitor is None, "no monitor thread before first bar"
assert tqdm.monitor_interval == 10
assert len(tqdm._instances) == 0

# --- trace lines 2-21: tqdm.__new__, which ignores the iterable --------
inst = tqdm.__new__(tqdm, chars)
try:
    assert type(inst) is tqdm

    # the list was not looked at: nothing configured yet
    for attr in ("iterable", "n", "total", "start_t", "pos", "sp"):
        assert not hasattr(inst, attr), attr

    # registered in the global WeakSet before __init__ ran
    assert len(tqdm._instances) == 1
    assert any(i is inst for i in tqdm._instances)
    assert hash(inst) == id(inst)  # tqdm.__hash__

    # the process-global write lock was constructed lazily, once
    lock = tqdm.get_lock()
    assert isinstance(lock, TqdmDefaultWriteLock)
    assert tqdm._lock is lock
    assert tqdm.get_lock() is lock, "get_lock must reuse the same lock"
    assert TqdmDefaultWriteLock.th_lock is not None
    assert hasattr(TqdmDefaultWriteLock, "mp_lock"), "create_mp_lock ran"
    assert lock.locks[-1] is TqdmDefaultWriteLock.th_lock
    assert lock.locks == [lk for lk in (TqdmDefaultWriteLock.mp_lock,
                                        TqdmDefaultWriteLock.th_lock)
                          if lk is not None]

    # the daemon monitor thread
    mon = tqdm.monitor
    assert isinstance(mon, TMonitor)
    assert mon.tqdm_cls is tqdm
    assert mon.sleep_interval == 10
    assert mon.name == "tqdm_monitor"
    assert mon.daemon is True
    assert mon.is_alive()
    assert mon.report() is True
    # our half-built instance has no `start_t`, so the monitor ignores it
    assert mon.get_instances() == []
finally:
    tqdm._instances.discard(inst)
    tqdm.monitor.exit()
    tqdm.monitor = None

print("chapter 1 verified")
