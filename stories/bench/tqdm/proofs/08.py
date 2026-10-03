"""Replays the scenario through the end of chapter 8 (trace lines 323-529)."""
from io import StringIO

from tqdm.std import EMA, Bar, tqdm
from tqdm.utils import disp_len

# --- 1. the frames, rendered from exactly the values the trace recorded ---------
frame_50 = tqdm.format_meter(
    n=2, total=4, elapsed=0.1105039119720459, ncols=None, prefix='Processing b: ',
    ascii=False, unit='it', unit_scale=False, rate=18.125303578991037,
    bar_format=None, postfix=None, unit_divisor=1000, initial=0, colour=None)
assert frame_50 == 'Processing b:  50%|\u2588\u2588\u2588\u2588\u2588     | 2/4 [00:00<00:00, 18.13it/s]', frame_50
assert disp_len(frame_50) == 59

# the two stale repaints forced by set_description: same n, same rate, later clock
for prefix, elapsed in (('Processing c: ', 0.1675429344177246),
                        ('Processing d: ', 0.22532391548156738)):
    stale = tqdm.format_meter(
        n=2, total=4, elapsed=elapsed, ncols=None, prefix=prefix, ascii=False,
        unit='it', unit_scale=False, rate=18.125303578991037, bar_format=None,
        postfix=None, unit_divisor=1000, initial=0, colour=None)
    assert stale == prefix[:-2] + ':  50%|\u2588\u2588\u2588\u2588\u2588     | 2/4 [00:00<00:00, 18.13it/s]', stale

frame_100 = tqdm.format_meter(
    n=4, total=4, elapsed=0.22755885124206543, ncols=None, prefix='Processing d: ',
    ascii=False, unit='it', unit_scale=False, rate=17.499504979897324,
    bar_format=None, postfix=None, unit_divisor=1000, initial=0, colour=None)
assert frame_100 == 'Processing d: 100%|\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588| 4/4 [00:00<00:00, 17.50it/s]', frame_100
assert disp_len(frame_100) == 59

assert f"{Bar(0.5, 10)}" == '\u2588\u2588\u2588\u2588\u2588     '
assert f"{Bar(1.0, 10)}" == '\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588'

# --- 2. the EMAs, replayed with the same inputs as the real run ------------------
ema_dn = EMA(0.3)
assert ema_dn(2) == 1.9999999999999996    # trace line 326 (first update)
assert ema_dn(2) == 2.0                   # trace line 479 (second update)

ema_miniters = EMA(0.3)
assert ema_miniters(1.8125303578991039) == 1.8125303578991034   # trace 374-375
assert ema_miniters(1.7086550917816143) == 1.7514272601829333   # trace 527-528

# --- 3. format_dict turns the two EMAs into the rate the frames displayed --------
rate_bar = tqdm(total=4, file=StringIO(), ascii=False)
rate_bar._ema_dn, rate_bar._ema_dt = (lambda: 1.9999999999999996), (lambda: 0.11034297943115233)
assert rate_bar.format_dict['rate'] == 18.125303578991037
rate_bar._ema_dn, rate_bar._ema_dt = (lambda: 2.0), (lambda: 0.1142889471615062)
assert rate_bar.format_dict['rate'] == 17.499504979897324
rate_bar._ema_dt = lambda: 0           # no timing sample yet -> None, not a crash
assert rate_bar.format_dict['rate'] is None
rate_bar.close()

# --- 4. the live run, with a fake clock standing in for sleep(0.05) --------------
out = StringIO()
clock = [0.0]
pbar = tqdm(["a", "b", "c", "d"], desc="Processing", file=out, ascii=False)
pbar._time = lambda: clock[0]
pbar.start_t = pbar.last_print_t = 0.0
assert pbar.miniters == 0 and pbar.dynamic_miniters is True

seen = []
for char in pbar:
    clock[0] += 0.055
    seen.append((char, pbar.n, pbar.last_print_n))
    pbar.set_description("Processing %s" % char)

# 'a' and 'b' were consumed while the published counter was still 0;
# 'c' and 'd' were consumed after the single update(2) that published 2.
assert seen == [('a', 0, 0), ('b', 0, 0), ('c', 2, 2), ('d', 2, 2)], seen
assert pbar.n == 4 and pbar.last_print_n == 4
assert abs(pbar.miniters - 1.8181818181818181) < 1e-6, pbar.miniters

output = out.getvalue()
assert 'Processing a:   0%|          | 0/4 [' in output      # stale, chapter 7
assert 'Processing b:   0%|          | 0/4 [' in output      # stale, chapter 7
assert 'Processing b:  50%|\u2588\u2588\u2588\u2588\u2588     | 2/4 [00:00<00:00, ' in output
assert 'Processing c:  50%|\u2588\u2588\u2588\u2588\u2588     | 2/4 [00:00<00:00, ' in output
assert 'Processing d:  50%|\u2588\u2588\u2588\u2588\u2588     | 2/4 [00:00<00:00, ' in output
assert 'Processing d: 100%|\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588| 4/4 [00:00<00:00, ' in output
assert output.index('Processing b:   0%') < output.index('Processing b:  50%')

# --- 5. update's return value is the "a frame was drawn" signal ------------------
published = tqdm(total=4, file=StringIO(), ascii=False, mininterval=0)
assert published.update(2) is True
assert published.n == 2 and published.last_print_n == 2
published.close()

withheld = tqdm(total=4, file=StringIO(), ascii=False, mininterval=100)
assert withheld.update(1) is None          # time gate shut: nothing printed
assert withheld.n == 1 and withheld.last_print_n == 0   # counter lags by design
withheld.close()

print("chapter 8 verified")
