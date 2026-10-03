import io
import sys

import click
from click import _compat, formatting, termui
from click.testing import BytesIOCopy, CliRunner, StreamMixer, make_input_stream


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


# --- CliRunner.__init__ (trace line 39) -------------------------------------
runner = CliRunner()
assert runner.charset == "utf-8"
assert runner.env == {}
assert runner.echo_stdin is False
assert runner.catch_exceptions is True
assert runner.capture == "sys"

try:
    CliRunner(capture="pipe")
except ValueError as e:
    assert "is not valid" in str(e)
else:
    raise AssertionError("capture='pipe' was accepted")

# --- make_input_stream (trace line 43) --------------------------------------
stream = make_input_stream("Click\n", "utf-8")
assert isinstance(stream, io.BytesIO)
assert stream.getvalue() == b"Click\n"

# --- make_env (45) and get_default_prog_name (56) ---------------------------
assert runner.make_env(None) == {}
assert runner.get_default_prog_name(hello) == "hello"

# --- StreamMixer / BytesIOCopy (trace lines 47-51) --------------------------
mixer = StreamMixer()
mixer.stdout.write(b"out")
mixer.stderr.write(b"err")
assert mixer.stdout.getvalue() == b"out"
assert mixer.stderr.getvalue() == b"err"
assert mixer.output.getvalue() == b"outerr"  # true write order, not a concat

# --- the isolation itself (trace lines 42-55) -------------------------------
saved_stdin, saved_stdout, saved_stderr = sys.stdin, sys.stdout, sys.stderr
saved_prompt = termui.visible_prompt_func
saved_strip = _compat.should_strip_ansi

with runner.isolation(input="Click\n", env=None, color=False) as outstreams:
    assert len(outstreams) == 3
    assert isinstance(outstreams[0], BytesIOCopy)
    assert isinstance(outstreams[1], BytesIOCopy)
    assert outstreams[0].copy_to is outstreams[2]
    assert outstreams[1].copy_to is outstreams[2]

    assert sys.stdin is not saved_stdin
    assert sys.stdout is not saved_stdout
    assert sys.stderr is not saved_stderr
    assert sys.stdin.name == "<stdin>" and sys.stdin.mode == "r"
    assert sys.stdout.name == "<stdout>" and sys.stdout.mode == "w"
    assert sys.stderr.name == "<stderr>"
    assert sys.stderr.errors == "backslashreplace"

    # capture="sys": fileno() stays unavailable, so os.dup2 cannot be aimed here
    try:
        sys.stdout.fileno()
    except io.UnsupportedOperation:
        pass
    else:
        raise AssertionError("fileno() succeeded in 'sys' capture mode")

    assert formatting.FORCED_WIDTH == 80
    assert termui.visible_prompt_func is not saved_prompt
    assert _compat.should_strip_ansi is not saved_strip
    assert _compat.should_strip_ansi(sys.stdout, None) is True  # color=False

    sys.stdout.write("a")
    sys.stdout.flush()
    sys.stderr.write("b")
    sys.stderr.flush()
    assert outstreams[0].getvalue() == b"a"
    assert outstreams[1].getvalue() == b"b"
    assert outstreams[2].getvalue() == b"ab"

    # the keystrokes are sitting unread, exactly as handed in
    assert sys.stdin.read() == "Click\n"
