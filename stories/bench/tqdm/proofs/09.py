"""Replay the scenario and assert what the data did while closing down."""
import io
import re
import sys
from time import sleep

from tqdm import tqdm
from tqdm.utils import disp_len


class Err(io.StringIO):
    """stderr stand-in that still reports a UTF-8 encoding (so ascii=False)."""
    encoding = 'utf-8'


# --- the exact closing frame from the trace, reproduced from its inputs ----
final = tqdm.format_meter(
    n=4, total=4, elapsed=0.230072021484375, ncols=None, prefix='Processing d: ',
    ascii=False, unit='it', unit_scale=False, rate=None, bar_format=None,
    postfix=None, unit_divisor=1000, initial=0, colour=None)
assert final == 'Processing d: 100%|██████████| 4/4 [00:00<00:00, 17.39it/s]', final
assert disp_len(final) == 59, disp_len(final)
# rate=None made format_meter fall back to the overall average n/elapsed
assert '17.39it/s' in final and '17.50it/s' not in final

# --- run the scenario, capturing stderr -----------------------------------
err = Err()
orig_stderr = sys.stderr
sys.stderr = err
try:
    chars = ["a", "b", "c", "d"]

    text = ""
    for char in tqdm(chars):
        sleep(0.05)
        text = text + char

    pbar = tqdm(chars, desc="Processing")
    assert pbar in tqdm._instances            # registered by __new__
    assert pbar.disable is False
    for char in pbar:
        sleep(0.05)
        pbar.set_description("Processing %s" % char)

    # __iter__'s `finally` already ran: self.n = 4; self.close()
    assert pbar.n == 4
    assert pbar.disable is True               # the latch in close()
    assert pbar not in tqdm._instances        # _decr_instances removed it
    assert abs(pbar.pos) == 0

    # close() swapped the EMA out for `lambda: None`
    assert pbar._ema_dt() is None

    # format_dict is still readable on a closed bar
    stats = dict(pbar.format_dict)
    out_after_stats = err.getvalue()

    # close() again, and via __del__: both are no-ops that print nothing
    assert pbar.close() is None
    assert pbar.__del__() is None
    assert err.getvalue() == out_after_stats
finally:
    sys.stderr = orig_stderr

assert text == "abcd", text
assert stats["n"] == stats["total"] == 4, stats
assert stats["rate"] is None, stats["rate"]
assert stats["elapsed"] > 0

captured = err.getvalue()
# leave=True: the final frame was drawn at pos=0 and terminated with '\n'
assert captured.endswith('\n'), repr(captured[-20:])
assert re.search(
    r'Processing d: 100%\|██████████\| 4/4 \[00:00<00:00, +\d+\.\d\dit/s\]\s*\n\Z',
    captured), repr(captured[-80:])
# the very first frame this bar ever drew
assert '\rProcessing:   0%|          | 0/4 [00:00<?, ?it/s]' in captured
print("ok")
