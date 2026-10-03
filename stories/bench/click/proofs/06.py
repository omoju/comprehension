import click
from click._utils import UNSET
from click.core import Context, ParameterSource, iter_params_for_processing


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


ctx = Context(hello, info_name="hello")

# Chapter 5 left off here.
parser = hello.make_parser(ctx)
opts, args, param_order = parser.parse_args(["--count=3"])
assert opts == {"count": "3"}
assert args == []
assert [p.name for p in param_order] == ["count"]

# The declaration list, with the injected help option cached by identity.
params = hello.get_params(ctx)
assert [p.name for p in params] == ["count", "name", "_click_default_help"]
help_opt = params[-1]
assert help_opt is hello.get_help_option(ctx)
assert help_opt.is_eager is True
assert help_opt.expose_value is False

# Eager first, then invocation order, then everything unmentioned.
order = iter_params_for_processing(param_order, params)
assert [p.name for p in order] == ["_click_default_help", "count", "name"]

# The help option's value comes from nowhere: the default, resolved lazily.
assert help_opt.default is UNSET
assert help_opt._default_explicit is False
assert help_opt.get_default(ctx) is False
assert ctx.get_parameter_source("_click_default_help") is None
value, source = help_opt.consume_value(ctx, opts)
assert value is False
assert source is ParameterSource.DEFAULT

# Full pass: converted, callback run, result discarded because expose_value=False.
value, rest = help_opt.handle_parse_result(ctx, opts, args)
assert value is None
assert rest == []
assert ctx.params == {}
assert ctx.get_parameter_source("_click_default_help") is ParameterSource.DEFAULT

print("chapter 6 verified")
