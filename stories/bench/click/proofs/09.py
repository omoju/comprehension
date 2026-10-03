import io
import sys

import click
import click.termui as termui
from click.core import Context
from click.exceptions import Exit
from click.testing import CliRunner, _NamedTextIOWrapper


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


runner = CliRunner()

# Globals swapped by isolation must come back exactly as they were.
before = (sys.stdin, sys.stdout, sys.stderr, termui.visible_prompt_func)
result = runner.invoke(hello, ["--count=3"], input="Click\n")
assert (sys.stdin, sys.stdout, sys.stderr, termui.visible_prompt_func) == before

# Success is exit code 0 via SystemExit, with no exception recorded.
assert result.exit_code == 0
assert result.exception is None
assert result.exc_info is not None
assert result.exc_info[0] is SystemExit
assert result.exc_info[1].code == 0

expected = b"Your name: Click\nHello, Click!\nHello, Click!\nHello, Click!\n"
assert result.stdout_bytes == expected
assert result.stderr_bytes == b""
assert result.output_bytes == expected
assert result.output == expected.decode("utf-8")
assert result.return_value is None

# ctx.exit closes the ExitStack *before* raising Exit.
calls = []
ctx = Context(hello)
ctx.call_on_close(lambda: calls.append("closed"))
raised = None
try:
    ctx.exit(0)
except Exit as e:
    raised = e
assert raised is not None and raised.exit_code == 0
assert calls == ["closed"]

# The callback's return value is not the exit code.
@click.command()
def returns_five():
    return 5

assert runner.invoke(returns_five, []).exit_code == 0

# catch_exceptions=True (the default) turns a crash into exit_code 1 + exception.
@click.command()
def boom():
    raise ValueError("boom")

crashed = runner.invoke(boom, [])
assert crashed.exit_code == 1
assert isinstance(crashed.exception, ValueError)

# A bad --count takes the ClickException arm: exit code 2, usage + hint on stderr.
bad = runner.invoke(hello, ["--count=x"], input="Click\n")
assert bad.exit_code == 2
assert "Try 'hello --help' for help." in bad.stderr
assert "Error: Invalid value for '--count': 'x' is not a valid integer." in bad.stderr

# _NamedTextIOWrapper.close is a no-op so the shared buffer survives it.
buf = io.BytesIO()
w = _NamedTextIOWrapper(buf, name="<x>", mode="w", encoding="utf-8")
w.write("hi")
w.flush()
w.close()
assert not buf.closed
assert buf.getvalue() == b"hi"

print("ok")
