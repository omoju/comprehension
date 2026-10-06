# Hand check · 20 judged claims (§5.1.5)

Write `agree`, `disagree` or `unsure` after **Omoju:** on each item. The arm is hidden; the key is in `eval/handcheck.key.json`.

## 1. httpx

**Claim:** The TestServer class extends uvicorn.Server

**Judge:** unverifiable — tests/conftest.py is not shown, so the TestServer definition cannot be checked.

tests/conftest.py:1-287
```
import asyncio
import json
import os
import threading
import time
import typing

import pytest
import trustme
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    load_pem_private_key,
)
from uvicorn.config import Config
from uvicorn.server import Server

import httpx
from tests.concurrency import sleep

ENVIRONMENT_VARIABLES = {
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "SSLKEYLOGFILE",
}


@pytest.fixture(scope="function", autouse=True)
def clean_environ():
    """Keeps os.environ clean for every test without having to mock os.environ"""
    original_environ = os.environ.copy()
    os.environ.clear()
    os.environ.update(
        {
…
```

**Omoju:** 

## 2. rich

**Claim:** `Style.__bool__` returns `False` for a null style.

**Judge:** supported — __bool__ returns `not self._null`, i.e. False for a null style.

rich/style.py:340-342
```
    def __bool__(self) -> bool:
        """A Style is false if it has no attributes, colors, or links."""
        return not self._null
```

**Omoju:** 

## 3. rich

**Claim:** `_check_buffer` deletes the buffer and drops output when `self.quiet` is set.

**Judge:** supported — _check_buffer does `del self._buffer[:]` and returns when self.quiet is True.

rich/console.py:2050-2052
```
        if self.quiet:
            del self._buffer[:]
            return
```

**Omoju:** 

## 4. rich

**Claim:** In `Table._get_cells`, the header style is `get_style(self.header_style or "") + get_style(column.header_style)`.

**Judge:** supported — The code is exactly header_style = get_style(self.header_style or "") + get_style(column.header_style).

rich/table.py:670-674
```
        if self.show_header:
            header_style = get_style(self.header_style or "") + get_style(
                column.header_style
            )
            _append((header_style, column.header))
```

**Omoju:** 

## 5. attrs

**Claim:** The attrs `attrs` namespace is built on top of the `attr` logic internally.

**Judge:** supported — The `attrs` package simply re-exports objects imported from `attr` and `attr._make`/`attr._next_gen`.

src/attrs/__init__.py:3-26
```
from attr import (
    NOTHING,
    Attribute,
    AttrsInstance,
    Converter,
    Factory,
    NothingType,
    _make_getattr,
    assoc,
    cmp_using,
    define,
    evolve,
    field,
    fields,
    fields_dict,
    frozen,
    has,
    make_class,
    mutable,
    resolve_types,
    validate,
)
from attr._make import ClassProps
from attr._next_gen import asdict, astuple, inspect
```
src/attrs/validators.py:3-3
```
from attr.validators import *  # noqa: F403
```

**Omoju:** 

## 6. click

**Claim:** `Command.format_help()` calls format_usage, format_help_text, format_options, and format_epilog in that order.

**Judge:** supported — `format_help` calls those four methods in exactly that relative order (with `format_arguments` additionally between help text and options).

src/click/core.py:1284-1301
```
    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes the help into the formatter if it exists.

        This is a low-level method called by :meth:`get_help`.

        This calls the following methods:

        -   :meth:`format_usage`
        -   :meth:`format_help_text`
        -   :meth:`format_arguments`
        -   :meth:`format_options`
        -   :meth:`format_epilog`
        """
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_arguments(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)
```

**Omoju:** 

## 7. requests

**Claim:** The Requests version is dynamically pulled from `requests.__version__.__version__`.

**Judge:** supported — The version string is defined in requests/__version__.py, re-exported in the package, and read dynamically (e.g. by docs/conf.py).

src/requests/__version__.py:8
```
__version__ = "2.34.2"
```
src/requests/__init__.py:159-170
```
from .__version__ import (
    __author__,
    __author_email__,
    __build__,
    __cake__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)
```
docs/conf.py:69-71
```
version = requests.__version__
# The full version, including alpha/beta/rc tags.
release = requests.__version__
```

**Omoju:** 

## 8. markupsafe

**Claim:** The C implementation in `_speedups.c` writes each replacement directly to an output buffer in a single pass.

**Judge:** contradicted — The C code makes two passes: GET_DELTA first scans the input to compute the size, then DO_ESCAPE writes to the new buffer.

src/markupsafe/_speedups.c:3-16
```
#define GET_DELTA(inp, inp_end, delta) \
	while (inp < inp_end) { \
		switch (*inp++) { \
		case '"': \
		case '\'': \
		case '&': \
			delta += 4; \
			break; \
		case '<': \
		case '>': \
			delta += 3; \
			break; \
		} \
	}
```
src/markupsafe/_speedups.c:83-96
```
	GET_DELTA(inp, inp_end, delta);
	if (!delta) {
		Py_INCREF(in);
		return (PyObject*)in;
	}

	out = PyUnicode_New(PyUnicode_GET_LENGTH(in) + delta,
						PyUnicode_IS_ASCII(in) ? 127 : 255);
	if (!out)
		return NULL;

	inp = PyUnicode_1BYTE_DATA(in);
	outp = PyUnicode_1BYTE_DATA(out);
	DO_ESCAPE(inp, inp_end, outp);
```

**Omoju:** 

## 9. tqdm

**Claim:** tqdm's CLI entry point is handled by tqdm.cli.main.

**Judge:** supported — The console script is declared as `tqdm = "tqdm.cli:main"`.

pyproject.toml:89-90
```
[project.scripts]
tqdm = "tqdm.cli:main"
```
tqdm/cli.py:156-162
```
def main(fp=sys.stderr, argv=None):
    """
    Parameters (internal use only)
    ---------
    fp  : file-like object for tqdm
    argv  : list (default: sys.argv[1:])
    """
```

**Omoju:** 

## 10. tqdm

**Claim:** The tqdm parameter `total` defaults to None.

**Judge:** supported — The `__init__` signature declares `total=None`.

tqdm/std.py:960-960
```
    def __init__(self, iterable=None, desc=None, total=None, leave=True, file=None,
```

**Omoju:** 

## 11. jinja

**Claim:** `EvalContext.__init__` calls `environment.autoescape` with the template name when it is callable

**Judge:** supported — EvalContext.__init__ calls environment.autoescape(template_name) when the attribute is callable.

src/jinja2/nodes.py:80-83
```
        if callable(environment.autoescape):
            self.autoescape = environment.autoescape(template_name)
        else:
            self.autoescape = environment.autoescape
```

**Omoju:** 

## 12. click

**Claim:** `_main_shell_completion` returns immediately when the completion environment variable is unset.

**Judge:** supported — `_main_shell_completion` reads the env var and returns early when `not instruction`.

src/click/core.py:1669-1672
```
        instruction = os.environ.get(complete_var)

        if not instruction:
            return
```

**Omoju:** 

## 13. tqdm

**Claim:** tqdm/contrib/telegram.py defines aliases tqdm and trange for tqdm_telegram.

**Judge:** supported — Aliases `tqdm = tqdm_telegram` and `trange = ttgrange` are defined.

tqdm/contrib/telegram.py:150-152
```
# Aliases
tqdm = tqdm_telegram
trange = ttgrange
```

**Omoju:** 

## 14. rich

**Claim:** `Text.rstrip_end` does nothing when the text length is below the given width.

**Judge:** supported — The body only executes when `text_length > size`, so nothing happens for shorter text.

rich/text.py:666-678
```
    def rstrip_end(self, size: int) -> None:
        """Remove whitespace beyond a certain width at the end of the text.

        Args:
            size (int): The desired size of the text.
        """
        text_length = len(self)
        if text_length > size:
            excess = text_length - size
            whitespace_match = _re_whitespace.search(self.plain)
            if whitespace_match is not None:
                whitespace_count = len(whitespace_match.group(0))
                self.right_crop(min(whitespace_count, excess))
```

**Omoju:** 

## 15. httpx

**Claim:** `BaseClient._merge_url` branches on `if merge_url.is_relative_url`

**Judge:** supported — The merging logic is guarded by `if merge_url.is_relative_url:`.

httpx/_client.py:397-397
```
        if merge_url.is_relative_url:
```

**Omoju:** 

## 16. click

**Claim:** `_make_cached_stream_func` builds a closure that reads `sys.stdout` at call time, looks it up in a `WeakKeyDictionary`, and only builds a wrapper on a cache miss.

**Judge:** supported — The factory's `func` calls `src_func()` (here `lambda: sys.stdout`) each call, consults a `WeakKeyDictionary` cache, and only calls `wrapper_func()` on a miss.

src/click/_compat.py:547-576
```
def _make_cached_stream_func(
    src_func: t.Callable[[], t.TextIO | None],
    wrapper_func: t.Callable[[], t.TextIO],
) -> t.Callable[[], t.TextIO | None]:
    cache: cabc.MutableMapping[t.TextIO, t.TextIO] = WeakKeyDictionary()

    def func() -> t.TextIO | None:
        stream = src_func()

        if stream is None:
            return None

        try:
            rv = cache.get(stream)
        except Exception:
            rv = None
        if rv is not None:
            return rv
        rv = wrapper_func()
        try:
            cache[stream] = rv
        except Exception:
            pass
        return rv

    return func


_default_text_stdin = _make_cached_stream_func(lambda: sys.stdin, get_text_stdin)
_default_text_stdout = _make_cached_stream_func(lambda: sys.stdout, get_text_stdout)
```

**Omoju:** 

## 17. attrs

**Claim:** attrs classes automatically generate `__match_args__` based on the attribute order to support structural pattern matching.

**Judge:** supported — `add_match_args` builds `__match_args__` as a tuple of field names (in attribute order) for init, non-kw_only fields, and is applied when match_args is true.

src/attr/_make.py:1118-1123
```
    def add_match_args(self):
        self._cls_dict["__match_args__"] = tuple(
            field.name
            for field in self._attrs
            if field.init and not field.kw_only
        )
```
src/attr/_make.py:1606-1607
```
        if match_args and not _has_own_attribute(cls, "__match_args__"):
            builder.add_match_args()
```

**Omoju:** 

## 18. markupsafe

**Claim:** `escape(None)` converts None to the string `'None'`.

**Judge:** supported — escape falls through to Markup(_escape_inner(str(None))) and the docstring shows escape(None) == Markup('None').

src/markupsafe/__init__.py:45-56
```
    return Markup(_escape_inner(str(s)))


def escape_silent(s: t.Any | None, /) -> Markup:
    """Like :func:`escape` but treats ``None`` as the empty string.
    Useful with optional values, as otherwise you get the string
    ``'None'`` when the value is ``None``.

    >>> escape(None)
    Markup('None')
    >>> escape_silent(None)
    Markup('')
```

**Omoju:** 

## 19. attrs

**Claim:** The pre-commit `interrogate` hook ensures the `tests` directory maintains docstring coverage.

**Judge:** unverifiable — The pre-commit configuration file's contents were not shown.

.pre-commit-config.yaml:1-32
```
---
ci:
  autoupdate_schedule: monthly

repos:
  - repo: https://github.com/econchick/interrogate
    rev: 1.7.0
    hooks:
      - id: interrogate
        args: [tests]

  - repo: https://github.com/codespell-project/codespell
    rev: v2.4.3
    hooks:
      - id: codespell
        args: [--exclude-file=tests/test_mypy.yml, --skip=*.svg]

  - repo: https://github.com/abravalheri/validate-pyproject
    rev: "0.26"
    hooks:
      - id: validate-pyproject
        # Optional extra validations from SchemaStore:
        additional_dependencies: ["validate-pyproject-schema-store[all]"]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
        exclude: docs/_static
      - id: check-toml
      - id: check-yaml
```

**Omoju:** 

## 20. tqdm

**Claim:** In `tqdm.__init__`, an explicit `total=float("inf")` is normalised to `None`.

**Judge:** supported — `if total == float("inf"): total = None  # same as unknown`.

tqdm/std.py:987-988
```
        if total == float("inf"):
            total = None  # same as unknown
```

**Omoju:** 
