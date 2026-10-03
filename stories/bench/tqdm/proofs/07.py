"""Chapter 7: set_description forces repaints that show a stale counter.

Replays the scenario's second bar up to the end of this chapter's span
(trace lines 227-322): yield 'a', set_description, yield 'b', set_description.
Run from the repository root with PYTHONPATH=.
"""
from io import StringIO
from time import sleep

from tqdm import tqdm
from tqdm.utils import disp_len


class Stream(StringIO):
    # tqdm reads `.encoding` to pick the charset; utf-8 stderr => unicode blocks
    encoding = 'utf-8'


out = Stream()
chars = ["a", "b", "c", "d"]
pbar = tqdm(chars, desc="Processing", file=out)

# --- state entering the chapter (end of Chapter 6) ---
assert pbar.desc == "Processing"
assert pbar.total == 4
assert pbar.n == 0 and pbar.last_print_n == 0
assert pbar.ascii is False          # unicode charset
assert pbar.miniters == 0           # counter gate: always open
assert pbar.mininterval == 0.1      # time gate: 100 ms
assert pbar.dynamic_miniters is True

it = iter(pbar)

# --- first item: yielded unchanged, counter untouched ---
char = next(it)
assert char == "a"
assert pbar.n == 0

sleep(0.05)
pbar.set_description("Processing %s" % char)

assert pbar.desc == "Processing a: "          # ': ' appended by set_description
d = pbar.format_dict
assert d["prefix"] == "Processing a: "
assert d["n"] == 0 and d["total"] == 4        # counter is stale
assert d["rate"] is None                      # no update() => no EMA interval yet
assert d["elapsed"] > 0                       # clock is live
frame_a = str(pbar)
assert frame_a == "Processing a:   0%|          | 0/4 [00:00<?, ?it/s]", frame_a
assert disp_len(frame_a) == 51

# --- resumption checks the gates and prints nothing, then yields 'b' ---
char = next(it)
assert char == "b"
assert pbar.n == 0 and pbar.last_print_n == 0  # time gate held it shut

sleep(0.05)
pbar.set_description("Processing %s" % char)

assert pbar.desc == "Processing b: "
frame_b = str(pbar)
assert frame_b == "Processing b:   0%|          | 0/4 [00:00<?, ?it/s]", frame_b
assert pbar.format_dict["n"] == 0              # two items consumed, still 0/4

# --- exactly three frames on the stream so far: init + two forced refreshes ---
written = out.getvalue()
assert written.count("\rProcessing:   0%|          | 0/4 ") == 1
assert written.count("\rProcessing a:   0%|          | 0/4 ") == 1
assert written.count("\rProcessing b:   0%|          | 0/4 ") == 1

# --- the trace's own snapshots render to the trace's own strings ---
assert tqdm.format_meter(
    n=0, total=4, elapsed=0.05352497100830078, ncols=None, prefix='Processing a: ',
    ascii=False, unit='it', unit_scale=False, rate=None, bar_format=None,
    postfix=None, unit_divisor=1000, initial=0, colour=None
) == 'Processing a:   0%|          | 0/4 [00:00<?, ?it/s]'
assert tqdm.format_meter(
    n=0, total=4, elapsed=0.10843706130981445, ncols=None, prefix='Processing b: ',
    ascii=False, unit='it', unit_scale=False, rate=None, bar_format=None,
    postfix=None, unit_divisor=1000, initial=0, colour=None
) == 'Processing b:   0%|          | 0/4 [00:00<?, ?it/s]'

pbar.close()  # cleanup only; belongs to a later chapter
print("chapter 7 proof ok")
