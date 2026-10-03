"""Replays scenario setup through tqdm.__init__ (trace lines 22-53)."""
import sys
from tqdm.std import tqdm
from tqdm.utils import DisableOnWriteError, _is_utf, _screen_shape_wrapper, _supports_unicode

chars = ["a", "b", "c", "d"]
bar = tqdm(chars)

# the list is stored verbatim, and `total` was borrowed from len()
assert bar.iterable is chars, bar.iterable
assert bar.total == 4, bar.total

# file defaulted to sys.stderr, then was wrapped by DisableOnWriteError
assert isinstance(bar.fp, DisableOnWriteError), type(bar.fp)
assert bar.fp._wrapped is sys.stderr, bar.fp._wrapped
assert bar.fp == sys.stderr, "wrapper forwards __eq__ to _wrapped"
# write/flush are the error-swallowing closures, not the raw methods
assert bar.fp.wrapper_getattr('write') is not sys.stderr.write

# terminal probe returned (None, None) in this environment -> no trimming
assert _screen_shape_wrapper()(bar.fp) == (None, None)
assert bar.ncols is None and bar.nrows is None, (bar.ncols, bar.nrows)

# unicode auto-detection from the stream's encoding
assert _is_utf('utf-8') is True
assert _supports_unicode(bar.fp) is True
assert bar.ascii is False, bar.ascii

# miniters=None turned on self-tuning; the other intervals passed through
assert bar.miniters == 0 and bar.dynamic_miniters is True
assert bar.mininterval == 0.1 and bar.maxinterval == 10.0
assert bar.smoothing == 0.3 and bar.delay == 0.0
assert bar.unit == 'it' and bar.unit_divisor == 1000
assert bar.desc == '' and bar.postfix is None

# three EMA accumulators, all unseeded (hence the "?it/s" first frame)
for ema in (bar._ema_dn, bar._ema_dt, bar._ema_miniters):
    assert ema.alpha == 0.3 and ema.last == 0 and ema.calls == 0

# a generator has no len(): total degrades to None instead of raising
gen_bar = tqdm(i for i in range(3))
assert gen_bar.total is None, gen_bar.total
# float("inf") is normalised to "unknown"
inf_bar = tqdm(total=float("inf"))
assert inf_bar.total is None, inf_bar.total

for b in (bar, gen_bar, inf_bar):
    b.close()
print("chapter 2 proof OK")
