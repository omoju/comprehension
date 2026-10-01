"""Typical tqdm usage: wrap an iterable and watch a smart progress meter.

Follows the first examples in README.rst ("Iterable-based" usage).
"""
from time import sleep

from tqdm import tqdm


def main():
    chars = ["a", "b", "c", "d"]

    # 1) simplest form: just wrap any iterable
    text = ""
    for char in tqdm(chars):
        sleep(0.05)  # pretend to do some work
        text = text + char

    # 2) instantiate outside the loop for manual control (description updates)
    pbar = tqdm(chars, desc="Processing")
    for char in pbar:
        sleep(0.05)
        pbar.set_description("Processing %s" % char)
    stats = dict(pbar.format_dict)
    pbar.close()

    return text, stats


if __name__ == "__main__":
    text, stats = main()
    assert text == "abcd", text
    assert stats["n"] == stats["total"] == 4, stats
