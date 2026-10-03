"""Chapter 3: position claimed under the lock, and a printer that remembers."""
from io import StringIO
from contextlib import redirect_stderr

from tqdm import tqdm
from tqdm.std import TqdmDefaultWriteLock

captured = StringIO()
with redirect_stderr(captured):
    t = tqdm(["a", "b", "c", "d"])

    # the lock used for position allocation is the one process-global lock
    assert isinstance(t._lock, TqdmDefaultWriteLock), type(t._lock)
    assert t._lock is tqdm.get_lock()

    # counters start in agreement, from `initial`
    assert t.n == 0, t.n
    assert t.last_print_n == 0, t.last_print_n
    assert t.total == 4, t.total

    # _get_free_pos skips the asking instance: line 0 is free, so pos == 0
    assert t.pos == 0, t.pos
    assert tqdm._get_free_pos(t) == 0, tqdm._get_free_pos(t)
    # without skipping it, line 0 is taken and the next free line is 1
    assert tqdm._get_free_pos() == 1, tqdm._get_free_pos()

    # gui=False, so a screen printer closure was built
    assert callable(t.sp)
    assert t.sp.__name__ == "print_status", t.sp.__name__

    # start_t is assigned last, together with last_print_t
    assert t.start_t == t.last_print_t

    t.close()

# the printer pads with spaces to erase the previous, longer frame
out = StringIO()
sp = tqdm.status_printer(out)
sp("abcdef")
assert out.getvalue() == "\rabcdef", repr(out.getvalue())
sp("xy")
assert out.getvalue() == "\rabcdef" + "\rxy    ", repr(out.getvalue())
