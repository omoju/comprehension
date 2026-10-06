# Hand check · 20 judged claims (§5.1.5)

Write `agree`, `disagree` or `unsure` after **Omoju:** on each item. The arm is hidden; the key is in `eval/handcheck.key.json`.

## 1. httpx

**Claim:** The TestServer class extends uvicorn.Server

**Judge:** unverifiable — `tests/conftest.py`, where a TestServer class would be defined, is not shown.

tests/conftest.py:1-1
```
import asyncio
```

**Omoju:** 

## 2. rich

**Claim:** `Style.__bool__` returns `False` for a null style.

**Judge:** unverifiable — Style.__bool__ is in rich/style.py, which is not shown.

rich/style.py:1-796
```
import sys
from functools import lru_cache
from itertools import count
from operator import attrgetter
from pickle import dumps, loads
from random import getrandbits
from typing import Any, Dict, Iterable, List, Optional, Type, Union, cast

from . import errors
from .color import Color, ColorParseError, ColorSystem, blend_rgb
from .repr import Result, rich_repr
from .terminal_theme import DEFAULT_TERMINAL_THEME, TerminalTheme

_hash_getter = attrgetter(
    "_color", "_bgcolor", "_attributes", "_set_attributes", "_link", "_meta"
)

# Style instances and style definitions are often interchangeable
StyleType = Union[str, "Style"]


_id_generator = count(getrandbits(24))


class _Bit:
    """A descriptor to get/set a style attribute bit."""

    __slots__ = ["bit"]

    def __init__(self, bit_no: int) -> None:
        self.bit = 1 << bit_no

    def __get__(self, obj: "Style", objtype: Type["Style"]) -> Optional[bool]:
        if obj._set_attributes & self.bit:
            return obj._attributes & self.bit != 0
        return None


@rich_repr
class Style:
…
```

**Omoju:** 

## 3. rich

**Claim:** `_check_buffer` deletes the buffer and drops output when `self.quiet` is set.

**Judge:** unverifiable — _check_buffer is defined in rich/console.py, which is excluded from the shown context.

rich/console.py:1-2698
```
import os
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from itertools import islice
from math import ceil
from os import PathLike
from time import monotonic
from types import FrameType, ModuleType, TracebackType
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    TextIO,
    Tuple,
    Type,
    Union,
    cast,
    runtime_checkable,
)

from rich._null_file import NULL_FILE

from . import errors, themes
from ._emoji_replace import _emoji_replace
from ._export_format import CONSOLE_HTML_FORMAT, CONSOLE_SVG_FORMAT
from ._fileno import get_fileno
from ._log_render import FormatTimeCallable, LogRender
…
```

**Omoju:** 

## 4. rich

**Claim:** In `Table._get_cells`, the header style is `get_style(self.header_style or "") + get_style(column.header_style)`.

**Judge:** unverifiable — Table._get_cells source is not present in the shown files.

rich/table.py:1-1015
```
from dataclasses import dataclass, field, replace
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from . import box, errors
from ._loop import loop_first_last, loop_last
from ._pick import pick_bool
from ._ratio import ratio_distribute, ratio_reduce
from .align import VerticalAlignMethod
from .jupyter import JupyterMixin
from .measure import Measurement
from .padding import Padding, PaddingDimensions
from .protocol import is_renderable
from .segment import Segment
from .style import Style, StyleType
from .text import Text, TextType

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        JustifyMethod,
        OverflowMethod,
        RenderableType,
        RenderResult,
    )


@dataclass
class Column:
    """Defines a column within a ~Table.
…
```

**Omoju:** 

## 5. attrs

**Claim:** The attrs `attrs` namespace is built on top of the `attr` logic internally.

**Judge:** supported — The docs state the `attrs` namespace is built on top of `attr`, and the `attrs` submodules simply re-export from `attr`.

docs/api.rst:17-18
```
The ``attrs`` namespace is built *on top of* ``attr`` -- which will *never* go away -- and is just as stable, since it doesn't constitute a rewrite.
To keep repetition low and this document at a reasonable size, the ``attr`` namespace is `documented on a separate page <api-attr>`.
```
src/attrs/converters.py:1-3
```
# SPDX-License-Identifier: MIT

from attr.converters import *  # noqa: F403
```

**Omoju:** 

## 6. click

**Claim:** `Command.format_help()` calls format_usage, format_help_text, format_options, and format_epilog in that order.

**Judge:** unverifiable — `src/click/core.py` is not included, so the call order inside `format_help()` cannot be checked.

docs/api.md:154-157
```
```{eval-rst}
.. autoclass:: Command
   :members:
```
```

**Omoju:** 

## 7. requests

**Claim:** The Requests version is dynamically pulled from `requests.__version__.__version__`.

**Judge:** supported — pyproject sets dynamic version via `attr = "requests.__version__.__version__"`.

pyproject.toml:80-81
```
[tool.setuptools.dynamic]
version = {attr = "requests.__version__.__version__"}
```

**Omoju:** 

## 8. markupsafe

**Claim:** The C implementation in `_speedups.c` writes each replacement directly to an output buffer in a single pass.

**Judge:** supported — DO_ESCAPE walks the input once writing escape sequences and copied chunks directly into the preallocated output buffer.

src/markupsafe/_speedups.c:18-72
```
#define DO_ESCAPE(inp, inp_end, outp) \
	{ \
		Py_ssize_t ncopy = 0; \
		while (inp < inp_end) { \
			switch (*inp) { \
			case '"': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = '#'; \
				*outp++ = '3'; \
				*outp++ = '4'; \
				*outp++ = ';'; \
				break; \
			case '\'': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = '#'; \
				*outp++ = '3'; \
				*outp++ = '9'; \
				*outp++ = ';'; \
				break; \
			case '&': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = 'a'; \
				*outp++ = 'm'; \
				*outp++ = 'p'; \
				*outp++ = ';'; \
				break; \
			case '<': \
				memcpy(outp, inp-ncopy, sizeof(*outp)*ncopy); \
				outp += ncopy; ncopy = 0; \
				*outp++ = '&'; \
				*outp++ = 'l'; \
				*outp++ = 't'; \
				*outp++ = ';'; \
				break; \
…
```
src/markupsafe/_speedups.c:94-97
```
	inp = PyUnicode_1BYTE_DATA(in);
	outp = PyUnicode_1BYTE_DATA(out);
	DO_ESCAPE(inp, inp_end, outp);
	return out;
```

**Omoju:** 

## 9. tqdm

**Claim:** tqdm's CLI entry point is handled by tqdm.cli.main.

**Judge:** supported — The console script entry point is declared as `tqdm = "tqdm.cli:main"`.

pyproject.toml:89-90
```
[project.scripts]
tqdm = "tqdm.cli:main"
```

**Omoju:** 

## 10. tqdm

**Claim:** The tqdm parameter `total` defaults to None.

**Judge:** supported — The documented signature shows `total=None` as the default.

README.rst:372-373
```
      def __init__(self, iterable=None, desc=None, total=None, leave=True,
                   file=None, ncols=None, mininterval=0.1,
```

**Omoju:** 

## 11. jinja

**Claim:** `EvalContext.__init__` calls `environment.autoescape` with the template name when it is callable

**Judge:** unverifiable — EvalContext is defined in src/jinja2/nodes.py, which is not shown.

src/jinja2/compiler.py:20-21
```
from .nodes import EvalContext
from .optimizer import Optimizer
```

**Omoju:** 

## 12. click

**Claim:** `_main_shell_completion` returns immediately when the completion environment variable is unset.

**Judge:** unverifiable — `_main_shell_completion` is in src/click/core.py, which is not shown.

src/click/__init__.py:1-10
```
"""
Click is a simple Python module inspired by the stdlib optparse to make
writing command line scripts fun. Unlike other modules, it's based
around a simple API that does not come with too much magic and is
composable.
"""

from __future__ import annotations

from .core import Argument as Argument
```

**Omoju:** 

## 13. tqdm

**Claim:** tqdm/contrib/telegram.py defines aliases tqdm and trange for tqdm_telegram.

**Judge:** unverifiable — tqdm/contrib/telegram.py is not shown, so the module-level aliases cannot be confirmed.

README.rst:713-713
```
- `tqdm.contrib.telegram <https://tqdm.github.io/docs/contrib.telegram/>`_: Posts to `Telegram <https://telegram.org>`__ bots
```

**Omoju:** 

## 14. rich

**Claim:** `Text.rstrip_end` does nothing when the text length is below the given width.

**Judge:** unverifiable — rich/text.py was not shown, so Text.rstrip_end's behaviour cannot be checked.

(no lines cited)

**Omoju:** 

## 15. httpx

**Claim:** `BaseClient._merge_url` branches on `if merge_url.is_relative_url`

**Judge:** supported — The method branches on `if merge_url.is_relative_url:`.

httpx/_client.py:397-397
```
        if merge_url.is_relative_url:
```

**Omoju:** 

## 16. click

**Claim:** `_make_cached_stream_func` builds a closure that reads `sys.stdout` at call time, looks it up in a `WeakKeyDictionary`, and only builds a wrapper on a cache miss.

**Judge:** supported — `_make_cached_stream_func` returns a closure that calls `src_func()` (e.g. `lambda: sys.stdout`) at call time, looks the stream up in a `WeakKeyDictionary` cache, and only calls `wrapper_func()` on a miss.

src/click/_compat.py:547-572
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
```
src/click/_compat.py:575-577
```
_default_text_stdin = _make_cached_stream_func(lambda: sys.stdin, get_text_stdin)
_default_text_stdout = _make_cached_stream_func(lambda: sys.stdout, get_text_stdout)
_default_text_stderr = _make_cached_stream_func(lambda: sys.stderr, get_text_stderr)
```

**Omoju:** 

## 17. attrs

**Claim:** attrs classes automatically generate `__match_args__` based on the attribute order to support structural pattern matching.

**Judge:** supported — The changelog documents that `__match_args__` are generated to support structural pattern matching, controlled by the `match_args` argument.

CHANGELOG.md:436-440
```
- `__match_args__` are now generated to support Python 3.10's
  [Structural Pattern Matching](https://docs.python.org/3.10/whatsnew/3.10.html#pep-634-structural-pattern-matching).
  This can be controlled by the `match_args` argument to the class decorators on Python 3.10 and later.
  On older versions, it is never added and the argument is ignored.
  [#815](https://github.com/python-attrs/attrs/issues/815)
```
docs/api-attr.rst:17
```
.. autofunction:: attr.s(these=None, repr_ns=None, repr=None, cmp=None, hash=None, init=None, slots=False, frozen=False, weakref_slot=True, str=False, auto_attribs=False, kw_only=False, cache_hash=False, auto_exc=False, eq=None, order=None, auto_detect=False, collect_by_mro=False, getstate_setstate=None, on_setattr=None, field_transformer=None, match_args=True, unsafe_hash=None)
```

**Omoju:** 

## 18. markupsafe

**Claim:** `escape(None)` converts None to the string `'None'`.

**Judge:** supported — The escape_silent docstring shows escape(None) == Markup('None') and the test asserts escape(None) == Markup(None).

src/markupsafe/__init__.py:52-56
```

    >>> escape(None)
    Markup('None')
    >>> escape_silent(None)
    Markup('')
```
tests/test_markupsafe.py:179-179
```
    assert escape(None) == Markup(None)
```

**Omoju:** 

## 19. attrs

**Claim:** The pre-commit `interrogate` hook ensures the `tests` directory maintains docstring coverage.

**Judge:** supported — The interrogate pre-commit hook is run with the `tests` argument and configured with fail-under = 100.

.pre-commit-config.yaml:6-10
```
  - repo: https://github.com/econchick/interrogate
    rev: 1.7.0
    hooks:
      - id: interrogate
        args: [tests]
```
pyproject.toml:210-214
```
[tool.interrogate]
omit-covered-files = true
verbose = 2
fail-under = 100
whitelist-regex = ["test_.*"]
```

**Omoju:** 

## 20. tqdm

**Claim:** In `tqdm.__init__`, an explicit `total=float("inf")` is normalised to `None`.

**Judge:** unverifiable — Only `reset(total=float('inf'))` setting `total` to None is asserted (plus a comment); the `__init__` normalisation is in the unshown tqdm/std.py.

tqdm/__init__.py:6-8
```
from .std import (
    TqdmDeprecationWarning, TqdmExperimentalWarning, TqdmKeyError, TqdmMonitorWarning,
    TqdmTypeError, TqdmWarning, tqdm, trange)
```
tests/tests_tqdm.py:955-963
```
def test_reset_inf(caperr):
    with tqdm(total=10, miniters=1, mininterval=0, maxinterval=0) as t:
        t.update(5)
        t.reset(total=float("inf"))
        t.update()
        # same as tqdm(total=float("inf")): treated as unknown
        assert t.total is None
    err = caperr()
    assert '1it' in err
```

**Omoju:** 
