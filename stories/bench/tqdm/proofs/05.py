"""Chapter 5: the second bar's __new__ reuses the lock and the monitor thread.

Replays the scenario from a clean interpreter up to the end of trace line 135.
Run from the repository root with PYTHONPATH=.
"""
import threading
from time import sleep

from tqdm.std import tqdm

# --- world before any bar exists (Chapter 1's preconditions) -----------------
assert tqdm.monitor is None, "class attribute starts as None"
assert not hasattr(tqdm, '_lock'), "importing tqdm must not build the lock"
assert tqdm.monitor_interval == 10

# --- first bar: trace lines 2-119 -------------------------------------------
chars = ["a", "b", "c", "d"]
text = ""
for char in tqdm(chars):
    sleep(0.05)
    text = text + char
assert text == "abcd", text

lock1 = tqdm.get_lock()
monitor1 = tqdm.monitor
assert monitor1 is not None, "first bar's __new__ started the monitor"
assert monitor1.tqdm_cls is tqdm
assert monitor1.sleep_interval == 10
assert monitor1.name == "tqdm_monitor"
assert monitor1.daemon is True
assert monitor1.is_alive()
assert monitor1.was_killed.is_set() is False
assert monitor1.report() is True

# --- second bar, this chapter's span: trace lines 120-135 -------------------
instance2 = tqdm.__new__(tqdm)                      # line 120
assert type(instance2) is tqdm                      # line 135's return
assert instance2 is not monitor1                    # sanity: distinct objects
assert hash(instance2) == id(instance2)             # line 127: __hash__ is id
assert any(i is instance2 for i in tqdm._instances)  # added to the WeakSet

assert tqdm.get_lock() is lock1                     # line 121-122: same lock
assert tqdm.monitor is monitor1                     # no replacement
assert monitor1.report() is True                    # line 129-130
assert monitor1.is_alive()
monitors = [t for t in threading.enumerate() if t.name == "tqdm_monitor"]
assert len(monitors) == 1, monitors               # one thread, not two
assert monitors[0] is monitor1

# __new__ has not touched any instance state yet
assert not hasattr(instance2, 'iterable')
assert not hasattr(instance2, 'pos')
assert not hasattr(instance2, 'start_t')

tqdm._instances.discard(instance2)
