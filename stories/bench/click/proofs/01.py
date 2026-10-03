import click
from click._utils import UNSET
from click.core import Command, Option
from click.parser import _split_opt
from click.types import INT, STRING, _guess_type, convert_type


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


# The decorated name is no longer a function.
assert isinstance(hello, Command)
assert hello.name == "hello"
assert hello.help == "Simple program that greets NAME for a total of COUNT times."
assert hello.callback.__name__ == "hello"
# __click_params__ was popped off the function and deleted.
assert not hasattr(hello.callback, "__click_params__")

# Bottom-up application, then reversed: source order is restored.
assert [p.name for p in hello.params] == ["count", "name"]
count_opt, name_opt = hello.params

# --name: trace lines 8-30.
assert isinstance(name_opt, Option)
assert name_opt.opts == ["--name"]
assert name_opt.secondary_opts == []
assert name_opt.default is UNSET
assert name_opt._default_explicit is False
assert name_opt.type is STRING
assert (name_opt.is_flag, name_opt._flag_needs_value) == (False, False)
assert name_opt.is_bool_flag is False
assert name_opt.prompt == "Your name"
assert name_opt.prompt_required is True
assert name_opt.required is False
assert name_opt.expose_value is True
assert name_opt.nargs == 1

# --count: same path, different default.
assert count_opt.opts == ["--count"]
assert count_opt.default == 1
assert count_opt._default_explicit is True
assert count_opt.type is INT
assert count_opt.is_flag is False
assert count_opt.prompt is None

# The helpers the declaration passed through.
assert _split_opt("--name") == ("--", "name")
assert _guess_type(None, UNSET) is type(UNSET)  # the Sentinel enum class
assert convert_type(None, UNSET) is STRING  # guessed junk falls back to STRING
assert convert_type(None, 1) is INT

print("chapter 1 ok")
