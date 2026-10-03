"""Chapter 4: parse_args -> make_parser -> get_params -> parser tables.

Run from the repository root with PYTHONPATH=src.
"""

import click
from click.core import Context
from click.parser import _split_opt
from click.types import BoolParamType


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


# --- state as the chapter opens -------------------------------------------
assert isinstance(hello, click.Command)
assert [p.name for p in hello.params] == ["count", "name"]
assert hello.no_args_is_help is False  # the NoArgsIsHelpError branch is not taken
assert hello._help_option is None  # nothing cached yet

ctx = Context(hello, info_name="hello", parent=None)
assert ctx.help_option_names == ["--help"]
assert ctx.token_normalize_func is None

# --- the help option nobody declared --------------------------------------
assert hello.get_help_option_names(ctx) == ["--help"]

help_opt = hello.get_help_option(ctx)
assert help_opt.name == "_click_default_help"
assert help_opt.opts == ["--help"]
assert help_opt.secondary_opts == []
assert help_opt.is_flag is True
assert help_opt.expose_value is False
assert help_opt.is_eager is True
assert isinstance(help_opt.type, BoolParamType)
assert help_opt.flag_activation_value is True

# Cached, and popped back off Command.params.
assert hello.get_help_option(ctx) is help_opt
assert hello._help_option is help_opt
assert [p.name for p in hello.params] == ["count", "name"]
assert [p.name for p in hello.get_params(ctx)] == [
    "count",
    "name",
    "_click_default_help",
]

# --- the parser the chapter hands on --------------------------------------
parser = hello.make_parser(ctx)

assert parser.allow_interspersed_args is True
assert parser.ignore_unknown_options is False
assert parser._opt_prefixes == {"-", "--"}
assert set(parser._long_opt) == {"--count", "--name", "--help"}
assert parser._short_opt == {}
assert parser._args == []

count_opt = parser._long_opt["--count"]
assert count_opt.dest == "count"
assert count_opt.action == "store"
assert count_opt.nargs == 1
assert count_opt.const is None
assert count_opt.takes_value is True

name_opt = parser._long_opt["--name"]
assert name_opt.dest == "name"
assert name_opt.action == "store"

parser_help_opt = parser._long_opt["--help"]
assert parser_help_opt.dest == "_click_default_help"
assert parser_help_opt.action == "store_const"
assert parser_help_opt.const is True
assert parser_help_opt.takes_value is False

# The spelling split that put them all in the long table.
assert _split_opt("--count") == ("--", "count")
assert _split_opt("--help") == ("--", "help")

print("chapter 4 ok")
