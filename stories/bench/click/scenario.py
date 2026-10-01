"""The README's first Click example, driven end to end.

A value travels from the command line (--count) and from the prompt (--name)
through Click's parsing, type conversion and callback invocation, and comes
back out as the rendered output of the command.
"""

import click
from click.testing import CliRunner


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


def main():
    runner = CliRunner()
    result = runner.invoke(hello, ["--count=3"], input="Click\n")
    print(result.output, end="")
    return result


if __name__ == "__main__":
    result = main()
    assert result.exit_code == 0, result.output
    assert result.output == (
        "Your name: Click\n"
        "Hello, Click!\n"
        "Hello, Click!\n"
        "Hello, Click!\n"
    )
