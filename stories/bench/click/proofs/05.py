"""Chapter 5: ['--count=3'] -> ({'count': '3'}, [], [<Option count>])."""

import click
from click.exceptions import NoSuchOption
from click.parser import _split_opt, _unpack_args


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


ctx = click.Context(hello, info_name="hello")

# The parser as Chapter 4 left it.
parser = hello.make_parser(ctx)
assert sorted(parser._long_opt) == ["--count", "--help", "--name"]
assert parser._short_opt == {}
assert parser._args == []
assert parser.allow_interspersed_args is True
assert parser.ignore_unknown_options is False

count_opt = parser._long_opt["--count"]
assert count_opt.dest == "count"
assert count_opt.action == "store"
assert count_opt.nargs == 1
assert count_opt.takes_value is True
assert _split_opt("--count") == ("--", "count")

# The span itself.
opts, largs, order = parser.parse_args(["--count=3"])
assert opts == {"count": "3"}, opts
assert isinstance(opts["count"], str)  # no type conversion at this layer
assert largs == []
assert order == [hello.params[0]]
assert order[0].name == "count"

# No positional parameters: nothing to deal out, nothing unclaimed.
assert _unpack_args([], []) == ((), [])

# Only the first "=" splits the token.
opts2, largs2, _ = hello.make_parser(ctx).parse_args(["--name=a=b"])
assert opts2 == {"name": "a=b"}
assert largs2 == []

# A bare "--" stops option parsing; the rest becomes leftovers.
opts3, largs3, order3 = hello.make_parser(ctx).parse_args(["--", "--count=3"])
assert opts3 == {}
assert largs3 == ["--count=3"]
assert order3 == []

# An unknown long option raises, with close matches attached.
try:
    hello.make_parser(ctx).parse_args(["--cont=3"])
except NoSuchOption as e:
    assert e.option_name == "--cont"
    assert e.possibilities == ["--count"]
else:
    raise AssertionError("expected NoSuchOption")

# ...unless the context is parsing resiliently, which swallows it entirely.
r_ctx = click.Context(hello, info_name="hello", resilient_parsing=True)
r_opts, r_largs, r_order = hello.make_parser(r_ctx).parse_args(["--cont=3"])
assert (r_opts, r_largs, r_order) == ({}, [], [])

print("chapter 5 ok")
