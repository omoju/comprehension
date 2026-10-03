import sys

import click
from click import _compat
from click import utils as click_utils
from click.testing import BytesIOCopy, CliRunner

seen = {}


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    ctx = click.get_current_context()
    seen["params"] = dict(ctx.params)
    seen["ctx_color"] = ctx.color
    seen["sys_stdout"] = sys.stdout
    # echo resolves its file through this cached helper; the runner's wrapper
    # is returned unchanged because its encoding/errors are compatible.
    seen["resolved"] = _compat._default_text_stdout()
    # The runner swapped in its own should_strip_ansi, which answers from the
    # color=False passed to invoke.
    seen["strip"] = click_utils.should_strip_ansi(sys.stdout, None)
    for _ in range(count):
        click.echo(f"Hello, {name}!")


# Spy on the byte-level writes that echo's text wrapper produces.
writes = []
original_write = BytesIOCopy.write


def spy_write(self, b):
    n = original_write(self, b)
    writes.append((bytes(b), n))
    return n


BytesIOCopy.write = spy_write
try:
    runner = CliRunner()
    runner.invoke(hello, ["--count=3"], input="Click\n")
finally:
    BytesIOCopy.write = original_write

# The parameters arrived as keyword arguments, already type-converted.
assert seen["params"] == {"count": 3, "name": "Click"}, seen["params"]

# _force_correct_text_stream returned the runner's stream unchanged.
assert seen["resolved"] is seen["sys_stdout"]
assert seen["sys_stdout"].encoding == "utf-8"
assert _compat.is_ascii_encoding("utf-8") is False
assert _compat._stream_is_misconfigured(seen["sys_stdout"]) is False

# Colour: ctx.color is None, and the patched should_strip_ansi says strip.
assert seen["ctx_color"] is None
assert seen["strip"] is True
# strip_ansi left the plain message alone, but it does remove real codes.
assert _compat.strip_ansi("Hello, Click!\n") == "Hello, Click!\n"
assert _compat.strip_ansi("\033[31mHello\033[0m") == "Hello"

# Three greetings of 14 bytes each, after the prompt echo from chapter 7.
assert writes[-3:] == [(b"Hello, Click!\n", 14)] * 3, writes
assert b"".join(b for b, _ in writes) == (
    b"Your name: Click\n"
    b"Hello, Click!\n"
    b"Hello, Click!\n"
    b"Hello, Click!\n"
), writes
