import click
from click.core import ParameterSource
from click.testing import CliRunner

seen = {}


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    ctx = click.get_current_context()
    seen["params"] = dict(ctx.params)
    seen["count_source"] = ctx.get_parameter_source("count")
    seen["name_source"] = ctx.get_parameter_source("name")
    seen["args"] = list(ctx.args)
    for _ in range(count):
        click.echo(f"Hello, {name}!")


runner = CliRunner()
result = runner.invoke(hello, ["--count=3"], input="Click\n")

# The scenario's run: '3' became an int, 'Click' came from the prompt.
assert result.exit_code == 0, result.output
assert seen["params"] == {"count": 3, "name": "Click"}
assert isinstance(seen["params"]["count"], int)
assert isinstance(seen["params"]["name"], str)
assert seen["count_source"] is ParameterSource.COMMANDLINE
assert seen["name_source"] is ParameterSource.PROMPT
assert seen["args"] == []

# The prompt was echoed into the captured stdout before the greetings.
assert result.output == (
    "Your name: Click\nHello, Click!\nHello, Click!\nHello, Click!\n"
)

# parse_args leaves the context at depth 0 (scope(cleanup=False) ran no
# teardown); main's own `with` is what takes it to 1.
ctx = hello.make_context("hello", ["--count=3", "--name=Click"])
assert ctx._depth == 0
assert ctx.params == {"count": 3, "name": "Click"}
assert ctx.args == []
with ctx:
    assert ctx._depth == 1

# Road not taken: a non-integer token fails as a UsageError, exit code 2,
# before --name is ever prompted for.
bad = runner.invoke(hello, ["--count=x"], input="Click\n")
assert bad.exit_code == 2, bad.output
assert "Invalid value for '--count'" in bad.stderr
assert "Your name:" not in bad.output

# Road not taken: a plain Command rejects leftover tokens.
try:
    hello.make_context("hello", ["--name=Click", "boom"])
except click.UsageError as e:
    assert "Got unexpected extra argument (boom)" in e.format_message()
else:
    raise AssertionError("extra argument was accepted")

# Road not taken: no input at all aborts non-zero instead of defaulting.
aborted = runner.invoke(hello, ["--count=3"], input="")
assert aborted.exit_code != 0
assert "Aborted!" in aborted.output

# A prompted value is processed twice: once via prompt()'s value_proc,
# once again in handle_parse_result.
calls = []


@click.command()
@click.option(
    "--who",
    prompt="Who",
    callback=lambda ctx, param, value: calls.append(value) or value,
)
def greet(who):
    click.echo(who)


r2 = runner.invoke(greet, [], input="Click\n")
assert r2.exit_code == 0, r2.output
assert calls == ["Click", "Click"], calls
