"""Replays chapter 4's span: the first frame, the four yields, the automatic close."""
import io
from contextlib import redirect_stderr
from time import sleep

from tqdm import tqdm
from tqdm.std import Bar
from tqdm.utils import disp_len

# --- 1) the frame itself, from the pure static formatter (std.py:462) ---------
frame = tqdm.format_meter(
    n=0, total=4, elapsed=0, ncols=None, prefix='', ascii=False, unit='it',
    unit_scale=False, rate=None, bar_format=None, postfix=None,
    unit_divisor=1000, initial=0, colour=None)
assert frame == '  0%|          | 0/4 [00:00<?, ?it/s]', repr(frame)

# pieces the trace recorded on the way there
assert tqdm.format_interval(0) == '00:00'
assert format(Bar(0.0, 10, charset=Bar.UTF, colour=None), '') == '          '
assert disp_len(frame) == 37, disp_len(frame)
assert len('\r' + frame) == 38          # the 38 returned by the stderr write

# no rate yet => '?it/s' and '?' remaining, not a division by zero
assert '?it/s' in frame and '<?,' in frame

# --- 2) the real bar, on a utf-8 stream standing in for stderr ----------------
class FakeStderr(io.StringIO):
    encoding = 'utf-8'          # so _supports_unicode -> True, ascii stays False

out = FakeStderr()
chars = ["a", "b", "c", "d"]
collected = []

with redirect_stderr(out):
    bar = tqdm(chars)                     # __new__ + __init__ + first refresh
    first = out.getvalue()
    assert first == '\r' + frame, repr(first)
    assert bar.pos == 0 and bar.total == 4 and bar.n == 0
    assert bar._ema_dt() == 0             # => format_dict['rate'] is None
    assert bar.ascii is False and bar.ncols is None and bar.nrows is None

    text = ""
    for char in bar:                      # __iter__ yields, finally closes
        sleep(0.05)
        collected.append(char)
        text = text + char

# items pass through unchanged, by identity
assert text == "abcd", text
assert all(a is b for a, b in zip(collected, chars))

# the finally reconciled the counter and closed the bar
assert bar.n == 4
assert bar.disable is True

# leave=True => a final frame plus a newline
final = out.getvalue()
assert '4/4' in final and final.endswith('\n'), repr(final[-70:])

# close is idempotent: __del__'s second call prints nothing more
bar.close()
assert out.getvalue() == final
