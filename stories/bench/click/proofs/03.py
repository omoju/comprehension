import os

import click

# --- the scenario's command, built exactly as in the README example ---


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


# --- trace 59-60: the completion door is checked first and lets us through ---

os.environ.pop("_HELLO_COMPLETE", None)
assert hello._main_shell_completion({}, "hello", None) is None

# The variable name is derived from prog_name. When it is set, the call
# diverts into the completion machinery and exits instead of returning
# None, so the command's own logic is never reached. An unknown shell
# makes shell_complete return 1, which becomes the exit status.
os.environ["_HELLO_COMPLETE"] = "nosuchshell_source"
try:
    diverted_code = "not raised"
    try:
        hello._main_shell_completion({}, "hello", None)
    except SystemExit as e:
        diverted_code = e.code
    assert diverted_code == 1, diverted_code
finally:
    del os.environ["_HELLO_COMPLETE"]

# --- trace 61-69: make_context builds the Context and enters its scope,
# then calls parse_args. Stand in for parse_args to observe the context
# exactly as this chapter's span leaves it. ---

seen = {}


def spy_parse_args(ctx, args):
    seen["args"] = list(args)
    seen["ctx"] = ctx
    seen["params"] = dict(ctx.params)
    seen["ctx_args"] = list(ctx.args)
    seen["depth"] = ctx._depth
    seen["current"] = click.get_current_context()
    return []


hello.parse_args = spy_parse_args
ctx = hello.make_context("hello", ["--count=3"])

# The arguments arrived untouched, and nothing has been parsed yet.
assert seen["args"] == ["--count=3"]
assert seen["params"] == {}
assert seen["ctx_args"] == []

# The context is live on the thread-local stack, entered twice
# (scope(cleanup=False) + __enter__), so teardown cannot run yet.
assert seen["ctx"] is ctx
assert seen["current"] is ctx
assert seen["depth"] == 2

# Defaults taken from the command and from literals, with no parent.
assert ctx.parent is None
assert ctx.command is hello
assert ctx.info_name == "hello"
assert ctx.help_option_names == ["--help"]
assert ctx.allow_extra_args is False
assert ctx.allow_interspersed_args is True
assert ctx.ignore_unknown_options is False
assert ctx.resilient_parsing is False
assert ctx.default_map is None
assert ctx.color is None
assert ctx.token_normalize_func is None

# No implicit environment reading is enabled for any option.
assert ctx.auto_envvar_prefix is None

# Bookkeeping starts empty.
assert ctx._parameter_source == {}
assert ctx._param_default_explicit == {}
assert ctx._opt_prefixes == set()
