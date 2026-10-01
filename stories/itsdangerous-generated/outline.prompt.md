# system

You plan code stories. A code story explains a repository as a narrative, in chapters, so that a
reader who has never seen the code comes away understanding how it works.

The formula: each chapter is a function. Its inputs are what earlier chapters established (characters met,
facts learned, open questions). Its outputs are what it adds. Later chapters build on earlier outputs, and the
order of chapters follows the order in which data and control actually move through the code, so the reader
never meets something before its prerequisites.

Use as many chapters as the repository needs to be understood: few for a small library, more for a large
system. Every chapter must earn its place. Characters are real things in the code (functions, classes, modules,
data). Facts are claims about behaviour that can be checked against the code. Open questions are things a
chapter raises that a later chapter answers; say which one in its "answers".

# user

Repository: pallets/itsdangerous at commit 672971d

<file_list>
.devcontainer/devcontainer.json  (17 lines)
.devcontainer/on-create-command.sh  (17 lines)
.editorconfig  (13 lines)
.github/ISSUE_TEMPLATE/bug-report.md  (27 lines)
.github/ISSUE_TEMPLATE/config.yml  (8 lines)
.github/ISSUE_TEMPLATE/feature-request.md  (15 lines)
.github/pull_request_template.md  (25 lines)
.github/workflows/pre-commit.yaml  (25 lines)
.github/workflows/publish.yaml  (47 lines)
.github/workflows/tests.yaml  (49 lines)
.gitignore  (8 lines)
.pre-commit-config.yaml  (18 lines)
.readthedocs.yaml  (10 lines)
CHANGES.rst  (292 lines)
LICENSE.txt  (28 lines)
README.md  (50 lines)
docs/Makefile  (19 lines)
docs/changes.rst  (4 lines)
docs/concepts.rst  (154 lines)
docs/conf.py  (55 lines)
docs/encoding.rst  (8 lines)
docs/exceptions.rst  (22 lines)
docs/index.rst  (63 lines)
docs/license.rst  (5 lines)
docs/make.bat  (35 lines)
docs/serializer.rst  (112 lines)
docs/signer.rst  (49 lines)
docs/timed.rst  (28 lines)
docs/url_safe.rst  (21 lines)
pyproject.toml  (205 lines)
src/itsdangerous/__init__.py  (17 lines)
src/itsdangerous/_json.py  (18 lines)
src/itsdangerous/encoding.py  (54 lines)
src/itsdangerous/exc.py  (106 lines)
src/itsdangerous/py.typed  (0 lines)
src/itsdangerous/serializer.py  (404 lines)
src/itsdangerous/signer.py  (266 lines)
src/itsdangerous/timed.py  (228 lines)
src/itsdangerous/url_safe.py  (83 lines)
tests/test_itsdangerous/__init__.py  (0 lines)
tests/test_itsdangerous/test_encoding.py  (37 lines)
tests/test_itsdangerous/test_serializer.py  (196 lines)
tests/test_itsdangerous/test_signer.py  (109 lines)
tests/test_itsdangerous/test_timed.py  (115 lines)
tests/test_itsdangerous/test_url_safe.py  (24 lines)
</file_list>

<file path=".devcontainer/devcontainer.json">
    1  {
    2    "name": "pallets/itsdangerous",
    3    "image": "mcr.microsoft.com/devcontainers/python:3",
    4    "customizations": {
    5      "vscode": {
    6        "settings": {
    7          "python.defaultInterpreterPath": "${workspaceFolder}/.venv",
    8          "python.terminal.activateEnvInCurrentTerminal": true,
    9          "python.terminal.launchArgs": [
   10            "-X",
   11            "dev"
   12          ]
   13        }
   14      }
   15    },
   16    "onCreateCommand": ".devcontainer/on-create-command.sh"
   17  }
</file>

<file path=".devcontainer/on-create-command.sh">
    1  #!/bin/bash
    2  set -e
    3  
    4  # Install uv if not already installed
    5  if ! command -v uv &> /dev/null; then
    6      echo "Installing uv..."
    7      curl -LsSf https://astral.sh/uv/install.sh | sh
    8      export PATH="$HOME/.cargo/bin:$PATH"
    9  fi
   10  
   11  # Create venv using uv and install dependencies
   12  echo "Creating virtual environment and installing dependencies..."
   13  uv sync
   14  
   15  # Install pre-commit hooks
   16  echo "Installing pre-commit hooks..."
   17  pre-commit install --install-hooks
</file>

<file path=".editorconfig">
    1  root = true
    2  
    3  [*]
    4  indent_style = space
    5  indent_size = 4
    6  insert_final_newline = true
    7  trim_trailing_whitespace = true
    8  end_of_line = lf
    9  charset = utf-8
   10  max_line_length = 88
   11  
   12  [*.{css,html,js,json,jsx,scss,ts,tsx,yaml,yml}]
   13  indent_size = 2
</file>

<file path=".github/ISSUE_TEMPLATE/bug-report.md">
    1  ---
    2  name: Bug report
    3  about: Report a bug in ItsDangerous (not other projects which depend on ItsDangerous)
    4  ---
    5  
    6  <!--
    7  This issue tracker is a tool to address bugs in ItsDangerous itself. Please use
    8  GitHub Discussions or the Pallets Discord for questions about your own code.
    9  
   10  Replace this comment with a clear outline of what the bug is.
   11  -->
   12  
   13  <!--
   14  Describe how to replicate the bug.
   15  
   16  Include a minimal reproducible example that demonstrates the bug.
   17  Include the full traceback if there was an exception.
   18  -->
   19  
   20  <!--
   21  Describe the expected behavior that should have happened but didn't.
   22  -->
   23  
   24  Environment:
   25  
   26  - Python version:
   27  - ItsDangerous version:
</file>

<file path=".github/ISSUE_TEMPLATE/config.yml">
    1  blank_issues_enabled: false
    2  contact_links:
    3    - name: Questions on Discussions
    4      url: https://github.com/pallets/itsdangerous/discussions/
    5      about: Ask questions about your own code on the Discussions tab.
    6    - name: Questions on Chat
    7      url: https://discord.gg/pallets
    8      about: Ask questions about your own code on our Discord chat.
</file>

<file path=".github/ISSUE_TEMPLATE/feature-request.md">
    1  ---
    2  name: Feature request
    3  about: Suggest a new feature for ItsDangerous
    4  ---
    5  
    6  <!--
    7  Replace this comment with a description of what the feature should do.
    8  Include details such as links to relevant specs or previous discussions.
    9  -->
   10  
   11  <!--
   12  Replace this comment with an example of the problem which this feature
   13  would resolve. Is this problem solvable without changes to ItsDangerous,
   14  such as by subclassing or using an extension?
   15  -->
</file>

<file path=".github/pull_request_template.md">
    1  <!--
    2  Before opening a PR, open a ticket describing the issue or feature the
    3  PR will address. An issue is not required for fixing typos in
    4  documentation, or other simple non-code changes.
    5  
    6  Replace this comment with a description of the change. Describe how it
    7  addresses the linked ticket.
    8  -->
    9  
   10  <!--
   11  Link to relevant issues or previous PRs, one per line. Use "fixes" to
   12  automatically close an issue.
   13  
   14  fixes #<issue number>
   15  -->
   16  
   17  <!--
   18  Ensure each step in CONTRIBUTING.rst is complete, especially the following:
   19  
   20  - Add tests that demonstrate the correct behavior of the change. Tests
   21    should fail without the change.
   22  - Add or update relevant docs, in the docs folder and in code.
   23  - Add an entry in CHANGES.rst summarizing the change and linking to the issue.
   24  - Add `.. versionchanged::` entries in any relevant code docs.
   25  -->
</file>

<file path=".github/workflows/pre-commit.yaml">
    1  name: pre-commit
    2  on:
    3    pull_request:
    4    push:
    5      branches: [main, stable]
    6  jobs:
    7    main:
    8      runs-on: ubuntu-latest
    9      steps:
   10        - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
   11        - uses: astral-sh/setup-uv@f0ec1fc3b38f5e7cd731bb6ce540c5af426746bb # v6.1.0
   12          with:
   13            enable-cache: true
   14            prune-cache: false
   15        - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
   16          id: setup-python
   17          with:
   18            python-version-file: pyproject.toml
   19        - uses: actions/cache@5a3ec84eff668545956fd18022155c47e93e2684 # v4.2.3
   20          with:
   21            path: ~/.cache/pre-commit
   22            key: pre-commit|${{ hashFiles('pyproject.toml', '.pre-commit-config.yaml') }}
   23        - run: uv run --locked --group pre-commit pre-commit run --show-diff-on-failure --color=always --all-files
   24        - uses: pre-commit-ci/lite-action@5d6cc0eb514c891a40562a58a8e71576c5c7fb43 # v1.1.0
   25          if: ${{ !cancelled() }}
</file>

<file path=".github/workflows/publish.yaml">
    1  name: Publish
    2  on:
    3    push:
    4      tags: ['*']
    5  jobs:
    6    build:
    7      runs-on: ubuntu-latest
    8      steps:
    9        - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
   10        - uses: astral-sh/setup-uv@f0ec1fc3b38f5e7cd731bb6ce540c5af426746bb # v6.1.0
   11          with:
   12            enable-cache: true
   13            prune-cache: false
   14        - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
   15          with:
   16            python-version-file: pyproject.toml
   17        - run: echo "SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)" >> $GITHUB_ENV
   18        - run: uv build
   19        - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
   20          with:
   21            path: ./dist
   22    create-release:
   23      needs: [build]
   24      runs-on: ubuntu-latest
   25      permissions:
   26        contents: write
   27      steps:
   28        - uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4.3.0
   29        - name: create release
   30          run: >
   31            gh release create --draft --repo ${{ github.repository }}
   32            ${{ github.ref_name }} artifact/*
   33          env:
   34            GH_TOKEN: ${{ github.token }}
   35    publish-pypi:
   36      needs: [build]
   37      environment:
   38        name: publish
   39        url: https://pypi.org/project/itsdangerous/${{ github.ref_name }}
   40      runs-on: ubuntu-latest
   41      permissions:
   42        id-token: write
   43      steps:
   44        - uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4.3.0
   45        - uses: pypa/gh-action-pypi-publish@76f52bc884231f62b9a034ebfe128415bbaabdfc # v1.12.4
   46          with:
   47            packages-dir: artifact/
</file>

<file path=".github/workflows/tests.yaml">
    1  name: Tests
    2  on:
    3    pull_request:
    4      paths-ignore: ['docs/**', 'README.md']
    5    push:
    6      branches: [main, stable]
    7      paths-ignore: ['docs/**', 'README.md']
    8  jobs:
    9    tests:
   10      name: ${{ matrix.name || matrix.python }}
   11      runs-on: ${{ matrix.os || 'ubuntu-latest' }}
   12      strategy:
   13        fail-fast: false
   14        matrix:
   15          include:
   16            - {python: '3.13'}
   17            - {name: Windows, python: '3.13', os: windows-latest}
   18            - {name: Mac, python: '3.13', os: macos-latest}
   19            - {python: '3.12'}
   20            - {python: '3.11'}
   21            - {python: '3.10'}
   22            - {name: PyPy, python: 'pypy-3.11', tox: pypy311}
   23      steps:
   24        - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
   25        - uses: astral-sh/setup-uv@f0ec1fc3b38f5e7cd731bb6ce540c5af426746bb # v6.1.0
   26          with:
   27            enable-cache: true
   28            prune-cache: false
   29        - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
   30          with:
   31            python-version: ${{ matrix.python }}
   32        - run: uv run --locked tox run -e ${{ matrix.tox || format('py{0}', matrix.python) }}
   33    typing:
   34      runs-on: ubuntu-latest
   35      steps:
   36        - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
   37        - uses: astral-sh/setup-uv@f0ec1fc3b38f5e7cd731bb6ce540c5af426746bb # v6.1.0
   38          with:
   39            enable-cache: true
   40            prune-cache: false
   41        - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
   42          with:
   43            python-version-file: pyproject.toml
   44        - name: cache mypy
   45          uses: actions/cache@5a3ec84eff668545956fd18022155c47e93e2684 # v4.2.3
   46          with:
   47            path: ./.mypy_cache
   48            key: mypy|${{ hashFiles('pyproject.toml') }}
   49        - run: uv run --locked tox run -e typing
</file>

<file path=".gitignore">
    1  .idea/
    2  .vscode/
    3  __pycache__/
    4  dist/
    5  .coverage*
    6  htmlcov/
    7  .tox/
    8  docs/_build/
</file>

<file path=".pre-commit-config.yaml">
    1  repos:
    2    - repo: https://github.com/astral-sh/ruff-pre-commit
    3      rev: 76e47323a83cd9795e4ff9a1de1c0d2eef610f17  # frozen: v0.11.11
    4      hooks:
    5        - id: ruff
    6        - id: ruff-format
    7    - repo: https://github.com/astral-sh/uv-pre-commit
    8      rev: 648bdbfd6bb1a82f132ecc2c666e0d1b2e4b0d94  # frozen: 0.7.8
    9      hooks:
   10        - id: uv-lock
   11    - repo: https://github.com/pre-commit/pre-commit-hooks
   12      rev: cef0300fd0fc4d2a87a85fa2093c6b283ea36f4b  # frozen: v5.0.0
   13      hooks:
   14        - id: check-merge-conflict
   15        - id: debug-statements
   16        - id: fix-byte-order-marker
   17        - id: trailing-whitespace
   18        - id: end-of-file-fixer
</file>

<file path=".readthedocs.yaml">
    1  version: 2
    2  build:
    3    os: ubuntu-24.04
    4    tools:
    5      python: '3.13'
    6    commands:
    7      - asdf plugin add uv
    8      - asdf install uv latest
    9      - asdf global uv latest
   10      - uv run --group docs sphinx-build -W -b dirhtml docs $READTHEDOCS_OUTPUT/html
</file>

<file path="CHANGES.rst">
    1  Version 2.3.0
    2  -------------
    3  
    4  Unreleased
    5  
    6  -   Drop support for Python 3.8 and 3.9.
    7  -   Remove previously deprecated code.
    8  
    9  
   10  Version 2.2.0
   11  -------------
   12  
   13  Released 2024-04-16
   14  
   15  -   Drop support for Python 3.7. :pr:`372`
   16  -   Use modern packaging metadata with ``pyproject.toml`` instead of ``setup.cfg``.
   17      :pr:`326`
   18  -   Use ``flit_core`` instead of ``setuptools`` as build backend.
   19  -   Deprecate the ``__version__`` attribute. Use feature detection, or
   20      ``importlib.metadata.version("itsdangerous")``, instead. :issue:`371`
   21  -   ``Serializer`` and the return type of ``dumps`` is generic for type checking.
   22      By default it is ``Serializer[str]`` and ``dumps`` returns a ``str``. If a
   23      different ``serializer`` argument is given, it will try to infer the return
   24      type of its ``dumps`` method. :issue:`347`
   25  -   The default ``hashlib.sha1`` may not be available in FIPS builds. Don't
   26      access it at import time so the developer has time to change the default.
   27      :issue:`375`
   28  
   29  
   30  Version 2.1.2
   31  -------------
   32  
   33  Released 2022-03-24
   34  
   35  -   Handle date overflow in timed unsign on 32-bit systems. :pr:`299`
   36  
   37  
   38  Version 2.1.1
   39  -------------
   40  
   41  Released 2022-03-09
   42  
   43  -   Handle date overflow in timed unsign. :pr:`296`
   44  
   45  
   46  Version 2.1.0
   47  -------------
   48  
   49  Released 2022-02-17
   50  
   51  -   Drop support for Python 3.6. :pr:`272`
   52  -   Remove previously deprecated code. :pr:`273`
   53  
   54      -   JWS functionality: Use a dedicated library such as Authlib
   55          instead.
   56      -   ``import itsdangerous.json``: Import ``json`` from the standard
   57          library instead.
   58  
   59  
   60  Version 2.0.1
   61  -------------
   62  
   63  Released 2021-05-18
   64  
   65  -   Mark top-level names as exported so type checking understands
   66      imports in user projects. :pr:`240`
   67  -   The ``salt`` argument to ``Serializer`` and ``Signer`` can be
   68      ``None`` again. :issue:`237`
   69  
   70  
   71  Version 2.0.0
   72  -------------
   73  
   74  Released 2021-05-11
   75  
   76  -   Drop support for Python 2 and 3.5.
   77  -   JWS support (``JSONWebSignatureSerializer``,
   78      ``TimedJSONWebSignatureSerializer``) is deprecated. Use a dedicated
   79      JWS/JWT library such as authlib instead. :issue:`129`
   80  -   Importing ``itsdangerous.json`` is deprecated. Import Python's
   81      ``json`` module instead. :pr:`152`
   82  -   Simplejson is no longer used if it is installed. To use a different
   83      library, pass it as ``Serializer(serializer=...)``. :issue:`146`
   84  -   ``datetime`` values are timezone-aware with ``timezone.utc``. Code
   85      using ``TimestampSigner.unsign(return_timestamp=True)`` or
   86      ``BadTimeSignature.date_signed`` may need to change. :issue:`150`
   87  -   If a signature has an age less than 0, it will raise
   88      ``SignatureExpired`` rather than appearing valid. This can happen if
   89      the timestamp offset is changed. :issue:`126`
   90  -   ``BadTimeSignature.date_signed`` is always a ``datetime`` object
   91      rather than an ``int`` in some cases. :issue:`124`
   92  -   Added support for key rotation. A list of keys can be passed as
   93      ``secret_key``, oldest to newest. The newest key is used for
   94      signing, all keys are tried for unsigning. :pr:`141`
   95  -   Removed the default SHA-512 fallback signer from
   96      ``default_fallback_signers``. :issue:`155`
   97  -   Add type information for static typing tools. :pr:`186`
   98  
   99  
  100  Version 1.1.0
  101  -------------
  102  
  103  Released 2018-10-26
  104  
  105  -   Change default signing algorithm back to SHA-1. :pr:`113`
  106  -   Added a default SHA-512 fallback for users who used the yanked 1.0.0
  107      release which defaulted to SHA-512. :pr:`114`
  108  -   Add support for fallback algorithms during deserialization to
  109      support changing the default in the future without breaking existing
  110      signatures. :pr:`113`
  111  -   Changed capitalization of packages back to lowercase as the change
  112      in capitalization broke some tooling. :pr:`113`
  113  
  114  
  115  Version 1.0.0
  116  -------------
  117  
  118  Released 2018-10-18
  119  
  120  YANKED
  121  
  122  *Note*: This release was yanked from PyPI because it changed the default
  123  algorithm to SHA-512. This decision was reverted in 1.1.0 and it remains
  124  at SHA1.
  125  
  126  -   Drop support for Python 2.6 and 3.3.
  127  -   Refactor code from a single module to a package. Any object in the
  128      API docs is still importable from the top-level ``itsdangerous``
  129      name, but other imports will need to be changed. A future release
  130      will remove many of these compatibility imports. :pr:`107`
  131  -   Optimize how timestamps are serialized and deserialized. :pr:`13`
  132  -   ``base64_decode`` raises ``BadData`` when it is passed invalid data.
  133      :pr:`27`
  134  -   Ensure value is bytes when signing to avoid a ``TypeError`` on
  135      Python 3. :issue:`29`
  136  -   Add a ``serializer_kwargs`` argument to ``Serializer``, which is
  137      passed to ``dumps`` during ``dump_payload``. :pr:`36`
  138  -   More compact JSON dumps for unicode strings. :issue:`38`
  139  -   Use the full timestamp rather than an offset, allowing dates before
  140      2011. :issue:`46`
  141  
  142      To retain compatibility with signers from previous versions,
  143      consider using `this shim <https://github.com/pallets/itsdangerous
  144      /issues/120#issuecomment-456913331>`_ when unsigning.
  145  -   Detect a ``sep`` character that may show up in the signature itself
  146      and raise a ``ValueError``. :issue:`62`
  147  -   Use a consistent signature for keyword arguments for
  148      ``Serializer.load_payload`` in subclasses. :issue:`74`, :pr:`75`
  149  -   Change default intermediate hash from SHA-1 to SHA-512. :pr:`80`
  150  -   Convert JWS exp header to an int when loading. :pr:`99`
  151  
  152  
  153  Version 0.24
  154  ------------
  155  
  156  Released 2014-03-28
  157  
  158  -   Added a ``BadHeader`` exception that is used for bad headers that
  159      replaces the old ``BadPayload`` exception that was reused in those
  160      cases.
  161  
  162  
  163  Version 0.23
  164  ------------
  165  
  166  Released 2013-08-08
  167  
  168  -   Fixed a packaging mistake that caused the tests and license files to
  169      not be included.
  170  
  171  
  172  Version 0.22
  173  ------------
  174  
  175  Released 2013-07-03
  176  
  177  -   Added support for ``TimedJSONWebSignatureSerializer``.
  178  -   Made it possible to override the signature verification function to
  179      allow implementing asymmetrical algorithms.
  180  
  181  
  182  Version 0.21
  183  ------------
  184  
  185  Released 2013-05-26
  186  
  187  -   Fixed an issue on Python 3 which caused invalid errors to be
  188      generated.
  189  
  190  
  191  Version 0.20
  192  ------------
  193  
  194  Released 2013-05-23
  195  
  196  -   Fixed an incorrect call into ``want_bytes`` that broke some uses of
  197      ItsDangerous on Python 2.6.
  198  
  199  
  200  Version 0.19
  201  ------------
  202  
  203  Released 2013-05-21
  204  
  205  -   Dropped support for 2.5 and added support for 3.3.
  206  
  207  
  208  Version 0.18
  209  ------------
  210  
  211  Released 2013-05-03
  212  
  213  -   Added support for JSON Web Signatures (JWS).
  214  
  215  
  216  Version 0.17
  217  ------------
  218  
  219  Released 2012-08-10
  220  
  221  -   Fixed a name error when overriding the digest method.
  222  
  223  
  224  Version 0.16
  225  ------------
  226  
  227  Released 2012-07-11
  228  
  229  -   Made it possible to pass unicode values to ``load_payload`` to make
  230      it easier to debug certain things.
  231  
  232  
  233  Version 0.15
  234  ------------
  235  
  236  Released 2012-07-11
  237  
  238  -   Made standalone ``load_payload`` more robust by raising one specific
  239      error if something goes wrong.
  240  -   Refactored exceptions to catch more cases individually, added more
  241      attributes.
  242  -   Fixed an issue that caused ``load_payload`` not work in some
  243      situations with timestamp based serializers
  244  -   Added an ``loads_unsafe`` method.
  245  
  246  
  247  Version 0.14
  248  ------------
  249  
  250  Released 2012-06-29
  251  
  252  -   API refactoring to support different key derivations.
  253  -   Added attributes to exceptions so that you can inspect the data even
  254      if the signature check failed.
  255  
  256  
  257  Version 0.13
  258  ------------
  259  
  260  Released 2012-06-10
  261  
  262  -   Small API change that enables customization of the digest module.
  263  
  264  
  265  Version 0.12
  266  ------------
  267  
  268  Released 2012-02-22
  269  
  270  -   Fixed a problem with the local timezone being used for the epoch
  271      calculation. This might invalidate some of your signatures if you
  272      were not running in UTC timezone. You can revert to the old behavior
  273      by monkey patching ``itsdangerous.EPOCH``.
  274  
  275  
  276  Version 0.11
  277  ------------
  278  
  279  Released 2011-07-07
  280  
  281  -   Fixed an uncaught value error.
  282  
  283  
  284  Version 0.10
  285  ------------
  286  
  287  Released 2011-06-25
  288  
  289  -   Refactored interface that the underlying serializers can be swapped
  290      by passing in a module instead of having to override the payload
  291      loaders and dumpers. This makes the interface more compatible with
  292      Django's recent changes.
</file>

<file path="LICENSE.txt">
    1  Copyright 2011 Pallets
    2  
    3  Redistribution and use in source and binary forms, with or without
    4  modification, are permitted provided that the following conditions are
    5  met:
    6  
    7  1.  Redistributions of source code must retain the above copyright
    8      notice, this list of conditions and the following disclaimer.
    9  
   10  2.  Redistributions in binary form must reproduce the above copyright
   11      notice, this list of conditions and the following disclaimer in the
   12      documentation and/or other materials provided with the distribution.
   13  
   14  3.  Neither the name of the copyright holder nor the names of its
   15      contributors may be used to endorse or promote products derived from
   16      this software without specific prior written permission.
   17  
   18  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   19  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   20  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
   21  PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
   22  HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
   23  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
   24  TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
   25  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
   26  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
   27  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
   28  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
</file>

<file path="README.md">
    1  <div align="center"><img src="https://raw.githubusercontent.com/pallets/itsdangerous/refs/heads/stable/docs/_static/itsdangerous-name.svg" alt="" height="150"></div>
    2  
    3  # ItsDangerous
    4  
    5  ... so better sign this
    6  
    7  Various helpers to pass data to untrusted environments and to get it
    8  back safe and sound. Data is cryptographically signed to ensure that a
    9  token has not been tampered with.
   10  
   11  It's possible to customize how data is serialized. Data is compressed as
   12  needed. A timestamp can be added and verified automatically while
   13  loading a token.
   14  
   15  
   16  ## A Simple Example
   17  
   18  Here's how you could generate a token for transmitting a user's id and
   19  name between web requests.
   20  
   21  ```python
   22  from itsdangerous import URLSafeSerializer
   23  auth_s = URLSafeSerializer("secret key", "auth")
   24  token = auth_s.dumps({"id": 5, "name": "itsdangerous"})
   25  
   26  print(token)
   27  # eyJpZCI6NSwibmFtZSI6Iml0c2Rhbmdlcm91cyJ9.6YP6T0BaO67XP--9UzTrmurXSmg
   28  
   29  data = auth_s.loads(token)
   30  print(data["name"])
   31  # itsdangerous
   32  ```
   33  
   34  
   35  ## Donate
   36  
   37  The Pallets organization develops and supports ItsDangerous and other
   38  popular packages. In order to grow the community of contributors and
   39  users, and allow the maintainers to devote more time to the projects,
   40  [please donate today][].
   41  
   42  [please donate today]: https://palletsprojects.com/donate
   43  
   44  ## Contributing
   45  
   46  See our [detailed contributing documentation][contrib] for many ways to
   47  contribute, including reporting issues, requesting features, asking or answering
   48  questions, and making PRs.
   49  
   50  [contrib]: https://palletsprojects.com/contributing/
</file>

<file path="docs/Makefile">
    1  # Minimal makefile for Sphinx documentation
    2  #
    3  
    4  # You can set these variables from the command line.
    5  SPHINXOPTS    =
    6  SPHINXBUILD   = sphinx-build
    7  SOURCEDIR     = .
    8  BUILDDIR      = _build
    9  
   10  # Put it first so that "make" without argument is like "make help".
   11  help:
   12  	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
   13  
   14  .PHONY: help Makefile
   15  
   16  # Catch-all target: route all unknown targets to Sphinx using the new
   17  # "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
   18  %: Makefile
   19  	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
</file>

<file path="docs/changes.rst">
    1  Changes
    2  =======
    3  
    4  .. include:: ../CHANGES.rst
</file>

<file path="docs/concepts.rst">
    1  General Concepts
    2  ================
    3  
    4  
    5  Serializer vs Signer
    6  --------------------
    7  
    8  ItsDangerous provides two levels of data handling. The :doc:`/signer` is
    9  the basic system that signs a given ``bytes`` value based on the given
   10  signing parameters. The :doc:`/serializer` wraps a signer to enable
   11  serializing and signing other data besides ``bytes``.
   12  
   13  Typically, you'll want to use a serializer, not a signer. You can
   14  configure the signing parameters through the serializer, and even
   15  provide fallback signers to upgrade old tokens to new parameters.
   16  
   17  
   18  The Secret Key
   19  --------------
   20  
   21  Signatures are secured by the ``secret_key``. Typically one secret key
   22  is used with all signers, and the salt is used to distinguish different
   23  contexts. Changing the secret key will invalidate existing tokens.
   24  
   25  It should be a long random string of bytes. This value must be kept
   26  secret and should not be saved in source code or committed to version
   27  control. If an attacker learns the secret key, they can change and
   28  resign data to look valid. If you suspect this happened, change the
   29  secret key to invalidate existing tokens.
   30  
   31  One way to keep the secret key separate is to read it from an
   32  environment variable. When deploying for the first time, generate a key
   33  and set the environment variable when running the application. All
   34  process managers (like systemd) and hosting services have a way to
   35  specify environment variables.
   36  
   37  .. code-block:: python
   38  
   39      import os
   40      from itsdangerous.serializer import Serializer
   41      SECRET_KEY = os.environ.get("SECRET_KEY")
   42      s = Serializer(SECRET_KEY)
   43  
   44  .. code-block:: text
   45  
   46      $ export SECRET_KEY="base64 encoded random bytes"
   47      $ python application.py
   48  
   49  One way to generate a key is to use :func:`os.urandom`.
   50  
   51  .. code-block:: text
   52  
   53      $ python3 -c 'import os; print(os.urandom(16).hex())'
   54  
   55  
   56  The Salt
   57  --------
   58  
   59  The salt is combined with the secret key to derive a unique key for
   60  distinguishing different contexts. Unlike the secret key, the salt
   61  doesn't have to be random, and can be saved in code. It only has to be
   62  unique between contexts, not private.
   63  
   64  For example, you want to email activation links to activate user
   65  accounts, and upgrade links to upgrade users to a paid accounts. If all
   66  you sign is the user id, and you don't use different salts, a user could
   67  reuse the token from the activation link to upgrade the account. If you
   68  use different salts, the signatures will be different and will not be
   69  valid in the other context.
   70  
   71  .. code-block:: python
   72  
   73      from itsdangerous.url_safe import URLSafeSerializer
   74  
   75      s1 = URLSafeSerializer("secret-key", salt="activate")
   76      s1.dumps(42)
   77      'NDI.MHQqszw6Wc81wOBQszCrEE_RlzY'
   78  
   79      s2 = URLSafeSerializer("secret-key", salt="upgrade")
   80      s2.dumps(42)
   81      'NDI.c0MpsD6gzpilOAeUPra3NShPXsE'
   82  
   83  The second serializer can't load data dumped with the first because the
   84  salts differ.
   85  
   86  .. code-block:: python
   87  
   88      s2.loads(s1.dumps(42))
   89      Traceback (most recent call last):
   90        ...
   91      BadSignature: Signature does not match
   92  
   93  Only the serializer with the same salt can load the data.
   94  
   95  .. code-block:: python
   96  
   97      s2.loads(s2.dumps(42))
   98      42
   99  
  100  
  101  Key Rotation
  102  ------------
  103  
  104  Key rotation can provide an extra layer of mitigation against an
  105  attacker discovering a secret key. A rotation system will keep a list of
  106  valid keys, generating a new key and removing the oldest key
  107  periodically. If it takes four weeks for an attacker to crack a key, but
  108  the key is rotated out after three weeks, they will not be able to use
  109  any keys they crack. However, if a user doesn't refresh their token
  110  within three weeks it will be invalid too.
  111  
  112  The system that generates and maintains this list is outside the scope
  113  of ItsDangerous, but ItsDangerous does support validating against a list
  114  of keys.
  115  
  116  Instead of passing a single key, you can pass a list of keys, oldest to
  117  newest. When signing the last (newest) key will be used, and when
  118  validating each key will be tried from newest to oldest before raising
  119  a validation error.
  120  
  121  .. code-block:: python
  122  
  123      SECRET_KEYS = ["2b9cd98e", "169d7886", "b6af09f5"]
  124  
  125      # sign some data with the latest key
  126      s = Serializer(SECRET_KEYS)
  127      t = s.dumps({"id": 42})
  128  
  129      # rotate a new key in and the oldest key out
  130      SECRET_KEYS.append("cf9b3588")
  131      del SECRET_KEYS[0]
  132  
  133      s = Serializer(SECRET_KEYS)
  134      s.loads(t)  # valid even though it was signed with a previous key
  135  
  136  
  137  Digest Method Security
  138  ----------------------
  139  
  140  A signer is configured with a ``digest_method``, a hash function that
  141  is used as an intermediate step when generating the HMAC signature. The
  142  default method is :func:`hashlib.sha1`. Occasionally, users are
  143  concerned about this default because they have heard about hash
  144  collisions with SHA-1.
  145  
  146  When used as the intermediate, iterated step in HMAC, SHA-1 is not
  147  insecure. In fact, even MD5 is still secure in HMAC. The security of the
  148  hash alone doesn't apply when used in HMAC.
  149  
  150  If a project considers SHA-1 a risk anyway, they can configure the
  151  signer with a different digest method such as :func:`hashlib.sha512`.
  152  A fallback signer for SHA-1 can be configured so that old tokens will be
  153  upgraded. SHA-512 produces a longer hash, so tokens will take up more
  154  space, which is relevant in cookies and URLs.
</file>

<file path="docs/conf.py">
    1  from pallets_sphinx_themes import get_version
    2  from pallets_sphinx_themes import ProjectLink
    3  
    4  # Project --------------------------------------------------------------
    5  
    6  project = "ItsDangerous"
    7  copyright = "2011 Pallets"
    8  author = "Pallets"
    9  release, version = get_version("itsdangerous")
   10  
   11  # General --------------------------------------------------------------
   12  
   13  default_role = "code"
   14  extensions = [
   15      "sphinx.ext.autodoc",
   16      "sphinx.ext.extlinks",
   17      "sphinx.ext.intersphinx",
   18      "sphinxcontrib.log_cabinet",
   19      "pallets_sphinx_themes",
   20  ]
   21  autoclass_content = "both"
   22  autodoc_member_order = "bysource"
   23  autodoc_typehints = "description"
   24  autodoc_preserve_defaults = True
   25  extlinks = {
   26      "issue": ("https://github.com/pallets/itsdangerous/issues/%s", "#%s"),
   27      "pr": ("https://github.com/pallets/itsdangerous/pull/%s", "#%s"),
   28  }
   29  intersphinx_mapping = {
   30      "python": ("https://docs.python.org/3/", None),
   31  }
   32  
   33  # HTML -----------------------------------------------------------------
   34  
   35  html_theme = "flask"
   36  html_theme_options = {"index_sidebar_logo": False}
   37  html_context = {
   38      "project_links": [
   39          ProjectLink("Donate", "https://palletsprojects.com/donate"),
   40          ProjectLink("PyPI Releases", "https://pypi.org/project/itsdangerous/"),
   41          ProjectLink("Source Code", "https://github.com/pallets/itsdangerous/"),
   42          ProjectLink("Issue Tracker", "https://github.com/pallets/itsdangerous/issues/"),
   43          ProjectLink("Chat", "https://discord.gg/pallets"),
   44      ]
   45  }
   46  html_sidebars = {
   47      "index": ["project.html", "localtoc.html", "searchbox.html", "ethicalads.html"],
   48      "**": ["localtoc.html", "relations.html", "searchbox.html", "ethicalads.html"],
   49  }
   50  singlehtml_sidebars = {"index": ["project.html", "localtoc.html", "ethicalads.html"]}
   51  html_static_path = ["_static"]
   52  html_favicon = "_static/itsdangerous-icon.svg"
   53  html_logo = "_static/itsdangerous-logo.svg"
   54  html_title = f"{project} Documentation ({version})"
   55  html_show_sourcelink = False
</file>

<file path="docs/encoding.rst">
    1  .. module:: itsdangerous.encoding
    2  
    3  Encoding Utilities
    4  ==================
    5  
    6  .. autofunction:: base64_encode
    7  
    8  .. autofunction:: base64_decode
</file>

<file path="docs/exceptions.rst">
    1  .. module:: itsdangerous.exc
    2  
    3  Exceptions
    4  ==========
    5  
    6  .. autoexception:: BadData
    7      :members:
    8  
    9  .. autoexception:: BadSignature
   10      :members:
   11  
   12  .. autoexception:: BadTimeSignature
   13      :members:
   14  
   15  .. autoexception:: SignatureExpired
   16      :members:
   17  
   18  .. autoexception:: BadHeader
   19      :members:
   20  
   21  .. autoexception:: BadPayload
   22      :members:
</file>

<file path="docs/index.rst">
    1  .. rst-class:: hide-header
    2  
    3  ItsDangerous
    4  ============
    5  
    6  .. image:: _static/itsdangerous-name.svg
    7      :align: center
    8      :height: 200px
    9  
   10  Sometimes you want to send some data to untrusted environments, then get
   11  it back later. To do this safely, the data must be signed to detect
   12  changes.
   13  
   14  Given a key only you know, you can cryptographically sign your data and
   15  hand it over to someone else. When you get the data back you can ensure
   16  that nobody tampered with it.
   17  
   18  The receiver can see the data, but they can not modify it unless they
   19  also have your key. So if you keep the key secret and complex, you will
   20  be fine.
   21  
   22  
   23  Installing
   24  ----------
   25  
   26  Install and update using `pip`_:
   27  
   28  .. code-block:: text
   29  
   30      pip install -U itsdangerous
   31  
   32  .. _pip: https://pip.pypa.io/en/stable/quickstart/
   33  
   34  
   35  Example Use Cases
   36  -----------------
   37  
   38  -   Sign a user ID in a URL and email it to them to unsubscribe from a
   39      newsletter. This way you don't need to generate one-time tokens and
   40      store them in the database. Same thing with any kind of activation
   41      link for accounts and similar things.
   42  -   Signed objects can be stored in cookies or other untrusted sources
   43      which means you don't need to have sessions stored on the server,
   44      which reduces the number of necessary database queries.
   45  -   Signed information can safely do a round trip between server and
   46      client in general which makes them useful for passing server-side
   47      state to a client and then back.
   48  
   49  
   50  Table of Contents
   51  -----------------
   52  
   53  .. toctree::
   54  
   55      concepts
   56      serializer
   57      signer
   58      exceptions
   59      timed
   60      url_safe
   61      encoding
   62      license
   63      changes
</file>

<file path="docs/license.rst">
    1  BSD-3-Clause License
    2  ====================
    3  
    4  .. literalinclude:: ../LICENSE.txt
    5      :language: text
</file>

<file path="docs/make.bat">
    1  @ECHO OFF
    2  
    3  pushd %~dp0
    4  
    5  REM Command file for Sphinx documentation
    6  
    7  if "%SPHINXBUILD%" == "" (
    8  	set SPHINXBUILD=sphinx-build
    9  )
   10  set SOURCEDIR=.
   11  set BUILDDIR=_build
   12  
   13  if "%1" == "" goto help
   14  
   15  %SPHINXBUILD% >NUL 2>NUL
   16  if errorlevel 9009 (
   17  	echo.
   18  	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
   19  	echo.installed, then set the SPHINXBUILD environment variable to point
   20  	echo.to the full path of the 'sphinx-build' executable. Alternatively you
   21  	echo.may add the Sphinx directory to PATH.
   22  	echo.
   23  	echo.If you don't have Sphinx installed, grab it from
   24  	echo.http://sphinx-doc.org/
   25  	exit /b 1
   26  )
   27  
   28  %SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
   29  goto end
   30  
   31  :help
   32  %SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
   33  
   34  :end
   35  popd
</file>

<file path="docs/serializer.rst">
    1  .. module:: itsdangerous.serializer
    2  
    3  Serialization Interface
    4  =======================
    5  
    6  The :doc:`/signer` only signs bytes. To sign other types, the
    7  :class:`Serializer` class provides a ``dumps``/``loads`` interface
    8  similar to Python's :mod:`json` module, which serializes the object to a
    9  string then signs that.
   10  
   11  Use :meth:`~Serializer.dumps` to serialize and sign the data:
   12  
   13  .. code-block:: python
   14  
   15      from itsdangerous.serializer import Serializer
   16      s = Serializer("secret-key")
   17      s.dumps([1, 2, 3, 4])
   18      b'[1, 2, 3, 4].r7R9RhGgDPvvWl3iNzLuIIfELmo'
   19  
   20  Use :meth:`~Serializer.loads` to verify the signature and deserialize
   21  the data.
   22  
   23  .. code-block:: python
   24  
   25      s.loads('[1, 2, 3, 4].r7R9RhGgDPvvWl3iNzLuIIfELmo')
   26      [1, 2, 3, 4]
   27  
   28  By default, data is serialized to JSON with the built-in :mod:`json`
   29  module. This internal serializer can be changed by subclassing.
   30  
   31  To record and validate the age of the signature, see :doc:`/timed`.
   32  To serialize to a format that is safe to use in URLs, see
   33  :doc:`/url_safe`.
   34  
   35  
   36  Responding to Failure
   37  ---------------------
   38  
   39  Exceptions have helpful attributes which allow you to inspect the
   40  payload if the signature check failed. This has to be done with extra
   41  care because at that point you know that someone tampered with your data
   42  but it might be useful for debugging purposes.
   43  
   44  .. code-block:: python
   45  
   46      from itsdangerous.serializer import Serializer
   47      from itsdangerous.exc import BadSignature, BadData
   48  
   49      s = URLSafeSerializer("secret-key")
   50      decoded_payload = None
   51  
   52      try:
   53          decoded_payload = s.loads(data)
   54          # This payload is decoded and safe
   55      except BadSignature as e:
   56          if e.payload is not None:
   57              try:
   58                  decoded_payload = s.load_payload(e.payload)
   59              except BadData:
   60                  pass
   61              # This payload is decoded but unsafe because someone
   62              # tampered with the signature. The decode (load_payload)
   63              # step is explicit because it might be unsafe to unserialize
   64              # the payload (think pickle instead of json!)
   65  
   66  If you don't want to inspect attributes to figure out what exactly went
   67  wrong you can also use :meth:`~Serializer.loads_unsafe`:
   68  
   69  .. code-block:: python
   70  
   71      sig_okay, payload = s.loads_unsafe(data)
   72  
   73  The first item in the returned tuple is a boolean that indicates if the
   74  signature was correct.
   75  
   76  
   77  Fallback Signers
   78  ----------------
   79  
   80  You may want to upgrade the signing parameters without invalidating
   81  existing signatures immediately. For example, you may decide that you
   82  want to use a different digest method. New signatures should use the new
   83  method, but old signatures should still validate.
   84  
   85  A list of ``fallback_signers`` can be given that will be tried if
   86  unsigning with the current signer fails. Each item in the list can be:
   87  
   88  -   A dict of ``signer_kwargs`` to instantiate the ``signer`` class
   89      passed to the serializer.
   90  -   A :class:`~itsdangerous.signer.Signer` class to instantiated with
   91      the ``secret_key``, ``salt``, and ``signer_kwargs`` passed to the
   92      serializer.
   93  -   A tuple of ``(signer_class, signer_kwargs)`` to instantiate the
   94      given class with the given args.
   95  
   96  For example, this is a serializer that signs using SHA-512, but will
   97  unsign using either SHA-512 or SHA-1:
   98  
   99  .. code-block:: python
  100  
  101      s = Serializer(
  102          signer_kwargs={"digest_method": hashlib.sha512},
  103          fallback_signers=[{"digest_method": hashlib.sha1}]
  104      )
  105  
  106  
  107  
  108  API
  109  ---
  110  
  111  .. autoclass:: Serializer
  112      :members:
</file>

<file path="docs/signer.rst">
    1  .. module:: itsdangerous.signer
    2  
    3  Signing Interface
    4  =================
    5  
    6  The most basic interface is the signing interface. The :class:`Signer`
    7  class can be used to attach a signature to a specific string:
    8  
    9  .. code-block:: python
   10  
   11      from itsdangerous import Signer
   12      s = Signer("secret-key")
   13      s.sign("my string")
   14      b'my string.wh6tMHxLgJqB6oY1uT73iMlyrOA'
   15  
   16  The signature is appended to the string, separated by a dot. To validate
   17  the string, use the :meth:`~Signer.unsign` method:
   18  
   19  .. code-block:: python
   20  
   21      s.unsign(b"my string.wh6tMHxLgJqB6oY1uT73iMlyrOA")
   22      b'my string'
   23  
   24  If unicode strings are provided, an implicit encoding to UTF-8 happens.
   25  However after unsigning you won't be able to tell if it was unicode or
   26  a bytestring.
   27  
   28  If the value is changed, the signature will no longer match, and
   29  unsigning will raise a :exc:`~itsdangerous.exc.BadSignature` exception:
   30  
   31  .. code-block:: python
   32  
   33      s.unsign(b"different string.wh6tMHxLgJqB6oY1uT73iMlyrOA")
   34      Traceback (most recent call last):
   35        ...
   36      BadSignature: Signature does not match
   37  
   38  To record and validate the age of a signature, see :doc:`/timed`.
   39  
   40  .. autoclass:: Signer
   41      :members:
   42  
   43  
   44  Signing Algorithms
   45  ------------------
   46  
   47  .. autoclass:: NoneAlgorithm
   48  
   49  .. autoclass:: HMACAlgorithm
</file>

<file path="docs/timed.rst">
    1  .. module:: itsdangerous.timed
    2  
    3  Signing With Timestamps
    4  =======================
    5  
    6  If you want to expire signatures you can use the
    7  :class:`TimestampSigner` class which adds timestamp information and
    8  signs it. On unsigning you can validate that the timestamp is not older
    9  than a given age.
   10  
   11  .. code-block:: python
   12  
   13      from itsdangerous import TimestampSigner
   14      s = TimestampSigner('secret-key')
   15      string = s.sign('foo')
   16  
   17  .. code-block:: python
   18  
   19      s.unsign(string, max_age=5)
   20      Traceback (most recent call last):
   21        ...
   22      itsdangerous.exc.SignatureExpired: Signature age 15 > 5 seconds
   23  
   24  .. autoclass:: TimestampSigner
   25      :members:
   26  
   27  .. autoclass:: TimedSerializer
   28      :members:
</file>

<file path="docs/url_safe.rst">
    1  .. module:: itsdangerous.url_safe
    2  
    3  URL Safe Serialization
    4  ======================
    5  
    6  Often it is helpful if you can pass these trusted strings in places
    7  where you only have a limited set of characters available. Because of
    8  this, ItsDangerous also provides URL safe serializers:
    9  
   10  .. code-block:: python
   11  
   12      from itsdangerous.url_safe import URLSafeSerializer
   13      s = URLSafeSerializer("secret-key")
   14      s.dumps([1, 2, 3, 4])
   15      'WzEsMiwzLDRd.wSPHqC0gR7VUqivlSukJ0IeTDgo'
   16      s.loads("WzEsMiwzLDRd.wSPHqC0gR7VUqivlSukJ0IeTDgo")
   17      [1, 2, 3, 4]
   18  
   19  .. autoclass:: URLSafeSerializer
   20  
   21  .. autoclass:: URLSafeTimedSerializer
</file>

<file path="pyproject.toml">
    1  [project]
    2  name = "itsdangerous"
    3  version = "2.3.0.dev"
    4  description = "Safely pass data to untrusted environments and back."
    5  readme = "README.md"
    6  license = "BSD-3-Clause"
    7  license-files = ["LICENSE.txt"]
    8  maintainers = [{name = "Pallets", email = "contact@palletsprojects.com"}]
    9  classifiers = [
   10      "Development Status :: 5 - Production/Stable",
   11      "Intended Audience :: Developers",
   12      "Operating System :: OS Independent",
   13      "Programming Language :: Python",
   14      "Typing :: Typed",
   15  ]
   16  requires-python = ">=3.10"
   17  
   18  [project.urls]
   19  Donate = "https://palletsprojects.com/donate"
   20  Documentation = "https://itsdangerous.palletsprojects.com/"
   21  Changes = "https://itsdangerous.palletsprojects.com/page/changes/"
   22  Source = "https://github.com/pallets/itsdangerous/"
   23  Chat = "https://discord.gg/pallets"
   24  
   25  [dependency-groups]
   26  dev = [
   27      "ruff",
   28      "tox",
   29      "tox-uv",
   30  ]
   31  docs = [
   32      "pallets-sphinx-themes",
   33      "sphinx",
   34      "sphinxcontrib-log-cabinet",
   35  ]
   36  docs-auto = [
   37      "sphinx-autobuild",
   38  ]
   39  gha-update = [
   40      "gha-update ; python_full_version >= '3.12'",
   41  ]
   42  pre-commit = [
   43      "pre-commit",
   44      "pre-commit-uv",
   45  ]
   46  tests = [
   47      "freezegun",
   48      "pytest",
   49  ]
   50  typing = [
   51      "mypy",
   52      "pyright",
   53      "pytest",
   54  ]
   55  
   56  [build-system]
   57  requires = ["flit_core<4"]
   58  build-backend = "flit_core.buildapi"
   59  
   60  [tool.flit.module]
   61  name = "itsdangerous"
   62  
   63  [tool.flit.sdist]
   64  include = [
   65      "docs/",
   66      "examples/",
   67      "tests/",
   68      "CHANGES.rst",
   69      "uv.lock"
   70  ]
   71  exclude = [
   72      "docs/_build/",
   73  ]
   74  
   75  [tool.uv]
   76  default-groups = ["dev", "pre-commit", "tests", "typing"]
   77  
   78  [tool.pytest.ini_options]
   79  testpaths = ["tests"]
   80  filterwarnings = [
   81      "error",
   82  ]
   83  
   84  [tool.coverage.run]
   85  branch = true
   86  source = ["jinja2", "tests"]
   87  
   88  [tool.coverage.paths]
   89  source = ["src", "*/site-packages"]
   90  
   91  [tool.coverage.report]
   92  exclude_also = [
   93      "if t.TYPE_CHECKING",
   94      "raise NotImplementedError",
   95      ": \\.{3}",
   96  ]
   97  
   98  [tool.mypy]
   99  python_version = "3.10"
  100  files = ["src"]
  101  show_error_codes = true
  102  pretty = true
  103  strict = true
  104  
  105  [tool.pyright]
  106  pythonVersion = "3.10"
  107  include = ["src"]
  108  typeCheckingMode = "standard"
  109  
  110  [tool.ruff]
  111  src = ["src"]
  112  fix = true
  113  show-fixes = true
  114  output-format = "full"
  115  
  116  [tool.ruff.lint]
  117  select = [
  118      "B",  # flake8-bugbear
  119      "E",  # pycodestyle error
  120      "F",  # pyflakes
  121      "I",  # isort
  122      "UP",  # pyupgrade
  123      "W",  # pycodestyle warning
  124  ]
  125  ignore = [
  126      "UP038",  # keep isinstance tuple
  127  ]
  128  
  129  [tool.ruff.lint.isort]
  130  force-single-line = true
  131  order-by-type = false
  132  
  133  [tool.gha-update]
  134  tag-only = [
  135      "slsa-framework/slsa-github-generator",
  136  ]
  137  
  138  [tool.tox]
  139  env_list = [
  140      "py3.13", "py3.12", "py3.11", "py3.10",
  141      "pypy311",
  142      "style",
  143      "typing",
  144      "docs",
  145  ]
  146  
  147  [tool.tox.env_run_base]
  148  description = "pytest on latest dependency versions"
  149  runner = "uv-venv-lock-runner"
  150  package = "wheel"
  151  wheel_build_env = ".pkg"
  152  constrain_package_deps = true
  153  use_frozen_constraints = true
  154  dependency_groups = ["tests"]
  155  commands = [[
  156      "pytest", "-v", "--tb=short", "--basetemp={env_tmp_dir}",
  157      {replace = "posargs", default = [], extend = true},
  158  ]]
  159  
  160  [tool.tox.env.style]
  161  description = "run all pre-commit hooks on all files"
  162  dependency_groups = ["pre-commit"]
  163  skip_install = true
  164  commands = [["pre-commit", "run", "--all-files"]]
  165  
  166  [tool.tox.env.typing]
  167  description = "run static type checkers"
  168  dependency_groups = ["typing"]
  169  commands = [
  170      ["mypy"],
  171      ["pyright"],
  172      ["pyright", "--verifytypes", "itsdangerous", "--ignoreexternal"],
  173  ]
  174  
  175  [tool.tox.env.docs]
  176  description = "build docs"
  177  dependency_groups = ["docs"]
  178  commands = [["sphinx-build", "-E", "-W", "-b", "dirhtml", "docs", "docs/_build/dirhtml"]]
  179  
  180  [tool.tox.env.docs-auto]
  181  description = "continuously rebuild docs and start a local server"
  182  dependency_groups = ["docs", "docs-auto"]
  183  commands = [["sphinx-autobuild", "-W", "-b", "dirhtml", "--watch", "src", "docs", "docs/_build/dirhtml"]]
  184  
  185  [tool.tox.env.update-actions]
  186  description = "update GitHub Actions pins"
  187  labels = ["update"]
  188  dependency_groups = ["gha-update"]
  189  skip_install = true
  190  commands = [["gha-update"]]
  191  
  192  [tool.tox.env.update-pre_commit]
  193  description = "update pre-commit pins"
  194  labels = ["update"]
  195  dependency_groups = ["pre-commit"]
  196  skip_install = true
  197  commands = [["pre-commit", "autoupdate", "--freeze", "-j4"]]
  198  
  199  [tool.tox.env.update-requirements]
  200  description = "update uv lock"
  201  labels = ["update"]
  202  dependency_groups = []
  203  no_default_groups = true
  204  skip_install = true
  205  commands = [["uv", "lock", {replace = "posargs", default = ["-U"], extend = true}]]
</file>

<file path="src/itsdangerous/__init__.py">
    1  from .encoding import base64_decode as base64_decode
    2  from .encoding import base64_encode as base64_encode
    3  from .encoding import want_bytes as want_bytes
    4  from .exc import BadData as BadData
    5  from .exc import BadHeader as BadHeader
    6  from .exc import BadPayload as BadPayload
    7  from .exc import BadSignature as BadSignature
    8  from .exc import BadTimeSignature as BadTimeSignature
    9  from .exc import SignatureExpired as SignatureExpired
   10  from .serializer import Serializer as Serializer
   11  from .signer import HMACAlgorithm as HMACAlgorithm
   12  from .signer import NoneAlgorithm as NoneAlgorithm
   13  from .signer import Signer as Signer
   14  from .timed import TimedSerializer as TimedSerializer
   15  from .timed import TimestampSigner as TimestampSigner
   16  from .url_safe import URLSafeSerializer as URLSafeSerializer
   17  from .url_safe import URLSafeTimedSerializer as URLSafeTimedSerializer
</file>

<file path="src/itsdangerous/_json.py">
    1  from __future__ import annotations
    2  
    3  import json as _json
    4  import typing as t
    5  
    6  
    7  class _CompactJSON:
    8      """Wrapper around json module that strips whitespace."""
    9  
   10      @staticmethod
   11      def loads(payload: str | bytes) -> t.Any:
   12          return _json.loads(payload)
   13  
   14      @staticmethod
   15      def dumps(obj: t.Any, **kwargs: t.Any) -> str:
   16          kwargs.setdefault("ensure_ascii", False)
   17          kwargs.setdefault("separators", (",", ":"))
   18          return _json.dumps(obj, **kwargs)
</file>

<file path="src/itsdangerous/encoding.py">
    1  from __future__ import annotations
    2  
    3  import base64
    4  import string
    5  import struct
    6  import typing as t
    7  
    8  from .exc import BadData
    9  
   10  
   11  def want_bytes(
   12      s: str | bytes, encoding: str = "utf-8", errors: str = "strict"
   13  ) -> bytes:
   14      if isinstance(s, str):
   15          s = s.encode(encoding, errors)
   16  
   17      return s
   18  
   19  
   20  def base64_encode(string: str | bytes) -> bytes:
   21      """Base64 encode a string of bytes or text. The resulting bytes are
   22      safe to use in URLs.
   23      """
   24      string = want_bytes(string)
   25      return base64.urlsafe_b64encode(string).rstrip(b"=")
   26  
   27  
   28  def base64_decode(string: str | bytes) -> bytes:
   29      """Base64 decode a URL-safe string of bytes or text. The result is
   30      bytes.
   31      """
   32      string = want_bytes(string, encoding="ascii", errors="ignore")
   33      string += b"=" * (-len(string) % 4)
   34  
   35      try:
   36          return base64.urlsafe_b64decode(string)
   37      except (TypeError, ValueError) as e:
   38          raise BadData("Invalid base64-encoded data") from e
   39  
   40  
   41  # The alphabet used by base64.urlsafe_*
   42  _base64_alphabet = f"{string.ascii_letters}{string.digits}-_=".encode("ascii")
   43  
   44  _int64_struct = struct.Struct(">Q")
   45  _int_to_bytes = _int64_struct.pack
   46  _bytes_to_int = t.cast("t.Callable[[bytes], tuple[int]]", _int64_struct.unpack)
   47  
   48  
   49  def int_to_bytes(num: int) -> bytes:
   50      return _int_to_bytes(num).lstrip(b"\x00")
   51  
   52  
   53  def bytes_to_int(bytestr: bytes) -> int:
   54      return _bytes_to_int(bytestr.rjust(8, b"\x00"))[0]
</file>

<file path="src/itsdangerous/exc.py">
    1  from __future__ import annotations
    2  
    3  import typing as t
    4  from datetime import datetime
    5  
    6  
    7  class BadData(Exception):
    8      """Raised if bad data of any sort was encountered. This is the base
    9      for all exceptions that ItsDangerous defines.
   10  
   11      .. versionadded:: 0.15
   12      """
   13  
   14      def __init__(self, message: str):
   15          super().__init__(message)
   16          self.message = message
   17  
   18      def __str__(self) -> str:
   19          return self.message
   20  
   21  
   22  class BadSignature(BadData):
   23      """Raised if a signature does not match."""
   24  
   25      def __init__(self, message: str, payload: t.Any | None = None):
   26          super().__init__(message)
   27  
   28          #: The payload that failed the signature test. In some
   29          #: situations you might still want to inspect this, even if
   30          #: you know it was tampered with.
   31          #:
   32          #: .. versionadded:: 0.14
   33          self.payload: t.Any | None = payload
   34  
   35  
   36  class BadTimeSignature(BadSignature):
   37      """Raised if a time-based signature is invalid. This is a subclass
   38      of :class:`BadSignature`.
   39      """
   40  
   41      def __init__(
   42          self,
   43          message: str,
   44          payload: t.Any | None = None,
   45          date_signed: datetime | None = None,
   46      ):
   47          super().__init__(message, payload)
   48  
   49          #: If the signature expired this exposes the date of when the
   50          #: signature was created. This can be helpful in order to
   51          #: tell the user how long a link has been gone stale.
   52          #:
   53          #: .. versionchanged:: 2.0
   54          #:     The datetime value is timezone-aware rather than naive.
   55          #:
   56          #: .. versionadded:: 0.14
   57          self.date_signed = date_signed
   58  
   59  
   60  class SignatureExpired(BadTimeSignature):
   61      """Raised if a signature timestamp is older than ``max_age``. This
   62      is a subclass of :exc:`BadTimeSignature`.
   63      """
   64  
   65  
   66  class BadHeader(BadSignature):
   67      """Raised if a signed header is invalid in some form. This only
   68      happens for serializers that have a header that goes with the
   69      signature.
   70  
   71      .. versionadded:: 0.24
   72      """
   73  
   74      def __init__(
   75          self,
   76          message: str,
   77          payload: t.Any | None = None,
   78          header: t.Any | None = None,
   79          original_error: Exception | None = None,
   80      ):
   81          super().__init__(message, payload)
   82  
   83          #: If the header is actually available but just malformed it
   84          #: might be stored here.
   85          self.header: t.Any | None = header
   86  
   87          #: If available, the error that indicates why the payload was
   88          #: not valid. This might be ``None``.
   89          self.original_error: Exception | None = original_error
   90  
   91  
   92  class BadPayload(BadData):
   93      """Raised if a payload is invalid. This could happen if the payload
   94      is loaded despite an invalid signature, or if there is a mismatch
   95      between the serializer and deserializer. The original exception
   96      that occurred during loading is stored on as :attr:`original_error`.
   97  
   98      .. versionadded:: 0.15
   99      """
  100  
  101      def __init__(self, message: str, original_error: Exception | None = None):
  102          super().__init__(message)
  103  
  104          #: If available, the error that indicates why the payload was
  105          #: not valid. This might be ``None``.
  106          self.original_error: Exception | None = original_error
</file>

<file path="src/itsdangerous/py.typed">

</file>

<file path="src/itsdangerous/serializer.py">
    1  from __future__ import annotations
    2  
    3  import collections.abc as cabc
    4  import json
    5  import typing as t
    6  
    7  from .encoding import want_bytes
    8  from .exc import BadPayload
    9  from .exc import BadSignature
   10  from .signer import _make_keys_list
   11  from .signer import Signer
   12  
   13  if t.TYPE_CHECKING:
   14      import typing_extensions as te
   15  
   16      # This should be either be str or bytes. To avoid having to specify the
   17      # bound type, it falls back to a union if structural matching fails.
   18      _TSerialized = te.TypeVar("_TSerialized", bound=str | bytes, default=str | bytes)
   19  else:
   20      # Still available at runtime on Python < 3.13, but without the default.
   21      _TSerialized = t.TypeVar("_TSerialized", bound=str | bytes)
   22  
   23  
   24  class _PDataSerializer(t.Protocol[_TSerialized]):
   25      def loads(self, payload: _TSerialized, /) -> t.Any: ...
   26      # A signature with additional arguments is not handled correctly by type
   27      # checkers right now, so an overload is used below for serializers that
   28      # don't match this strict protocol.
   29      def dumps(self, obj: t.Any, /) -> _TSerialized: ...
   30  
   31  
   32  # Use TypeIs once it's available in typing_extensions or 3.13.
   33  def is_text_serializer(
   34      serializer: _PDataSerializer[t.Any],
   35  ) -> te.TypeGuard[_PDataSerializer[str]]:
   36      """Checks whether a serializer generates text or binary."""
   37      return isinstance(serializer.dumps({}), str)
   38  
   39  
   40  class Serializer(t.Generic[_TSerialized]):
   41      """A serializer wraps a :class:`~itsdangerous.signer.Signer` to
   42      enable serializing and securely signing data other than bytes. It
   43      can unsign to verify that the data hasn't been changed.
   44  
   45      The serializer provides :meth:`dumps` and :meth:`loads`, similar to
   46      :mod:`json`, and by default uses :mod:`json` internally to serialize
   47      the data to bytes.
   48  
   49      The secret key should be a random string of ``bytes`` and should not
   50      be saved to code or version control. Different salts should be used
   51      to distinguish signing in different contexts. See :doc:`/concepts`
   52      for information about the security of the secret key and salt.
   53  
   54      :param secret_key: The secret key to sign and verify with. Can be a
   55          list of keys, oldest to newest, to support key rotation.
   56      :param salt: Extra key to combine with ``secret_key`` to distinguish
   57          signatures in different contexts.
   58      :param serializer: An object that provides ``dumps`` and ``loads``
   59          methods for serializing data to a string. Defaults to
   60          :attr:`default_serializer`, which defaults to :mod:`json`.
   61      :param serializer_kwargs: Keyword arguments to pass when calling
   62          ``serializer.dumps``.
   63      :param signer: A ``Signer`` class to instantiate when signing data.
   64          Defaults to :attr:`default_signer`, which defaults to
   65          :class:`~itsdangerous.signer.Signer`.
   66      :param signer_kwargs: Keyword arguments to pass when instantiating
   67          the ``Signer`` class.
   68      :param fallback_signers: List of signer parameters to try when
   69          unsigning with the default signer fails. Each item can be a dict
   70          of ``signer_kwargs``, a ``Signer`` class, or a tuple of
   71          ``(signer, signer_kwargs)``. Defaults to
   72          :attr:`default_fallback_signers`.
   73  
   74      .. versionchanged:: 2.0
   75          Added support for key rotation by passing a list to
   76          ``secret_key``.
   77  
   78      .. versionchanged:: 2.0
   79          Removed the default SHA-512 fallback signer from
   80          ``default_fallback_signers``.
   81  
   82      .. versionchanged:: 1.1
   83          Added support for ``fallback_signers`` and configured a default
   84          SHA-512 fallback. This fallback is for users who used the yanked
   85          1.0.0 release which defaulted to SHA-512.
   86  
   87      .. versionchanged:: 0.14
   88          The ``signer`` and ``signer_kwargs`` parameters were added to
   89          the constructor.
   90      """
   91  
   92      #: The default serialization module to use to serialize data to a
   93      #: string internally. The default is :mod:`json`, but can be changed
   94      #: to any object that provides ``dumps`` and ``loads`` methods.
   95      default_serializer: _PDataSerializer[t.Any] = json
   96  
   97      #: The default ``Signer`` class to instantiate when signing data.
   98      #: The default is :class:`itsdangerous.signer.Signer`.
   99      default_signer: type[Signer] = Signer
  100  
  101      #: The default fallback signers to try when unsigning fails.
  102      default_fallback_signers: list[
  103          dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  104      ] = []
  105  
  106      # Serializer[str] if no data serializer is provided, or if it returns str.
  107      @t.overload
  108      def __init__(
  109          self: Serializer[str],
  110          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  111          salt: str | bytes | None = b"itsdangerous",
  112          serializer: None | _PDataSerializer[str] = None,
  113          serializer_kwargs: dict[str, t.Any] | None = None,
  114          signer: type[Signer] | None = None,
  115          signer_kwargs: dict[str, t.Any] | None = None,
  116          fallback_signers: list[
  117              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  118          ]
  119          | None = None,
  120      ): ...
  121  
  122      # Serializer[bytes] with a bytes data serializer positional argument.
  123      @t.overload
  124      def __init__(
  125          self: Serializer[bytes],
  126          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  127          salt: str | bytes | None,
  128          serializer: _PDataSerializer[bytes],
  129          serializer_kwargs: dict[str, t.Any] | None = None,
  130          signer: type[Signer] | None = None,
  131          signer_kwargs: dict[str, t.Any] | None = None,
  132          fallback_signers: list[
  133              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  134          ]
  135          | None = None,
  136      ): ...
  137  
  138      # Serializer[bytes] with a bytes data serializer keyword argument.
  139      @t.overload
  140      def __init__(
  141          self: Serializer[bytes],
  142          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  143          salt: str | bytes | None = b"itsdangerous",
  144          *,
  145          serializer: _PDataSerializer[bytes],
  146          serializer_kwargs: dict[str, t.Any] | None = None,
  147          signer: type[Signer] | None = None,
  148          signer_kwargs: dict[str, t.Any] | None = None,
  149          fallback_signers: list[
  150              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  151          ]
  152          | None = None,
  153      ): ...
  154  
  155      # Fall back with a positional argument. If the strict signature of
  156      # _PDataSerializer doesn't match, fall back to a union, requiring the user
  157      # to specify the type.
  158      @t.overload
  159      def __init__(
  160          self,
  161          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  162          salt: str | bytes | None,
  163          serializer: t.Any,
  164          serializer_kwargs: dict[str, t.Any] | None = None,
  165          signer: type[Signer] | None = None,
  166          signer_kwargs: dict[str, t.Any] | None = None,
  167          fallback_signers: list[
  168              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  169          ]
  170          | None = None,
  171      ): ...
  172  
  173      # Fall back with a keyword argument.
  174      @t.overload
  175      def __init__(
  176          self,
  177          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  178          salt: str | bytes | None = b"itsdangerous",
  179          *,
  180          serializer: t.Any,
  181          serializer_kwargs: dict[str, t.Any] | None = None,
  182          signer: type[Signer] | None = None,
  183          signer_kwargs: dict[str, t.Any] | None = None,
  184          fallback_signers: list[
  185              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  186          ]
  187          | None = None,
  188      ): ...
  189  
  190      def __init__(
  191          self,
  192          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  193          salt: str | bytes | None = b"itsdangerous",
  194          serializer: t.Any | None = None,
  195          serializer_kwargs: dict[str, t.Any] | None = None,
  196          signer: type[Signer] | None = None,
  197          signer_kwargs: dict[str, t.Any] | None = None,
  198          fallback_signers: list[
  199              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  200          ]
  201          | None = None,
  202      ):
  203          #: The list of secret keys to try for verifying signatures, from
  204          #: oldest to newest. The newest (last) key is used for signing.
  205          #:
  206          #: This allows a key rotation system to keep a list of allowed
  207          #: keys and remove expired ones.
  208          self.secret_keys: list[bytes] = _make_keys_list(secret_key)
  209  
  210          if salt is not None:
  211              salt = want_bytes(salt)
  212              # if salt is None then the signer's default is used
  213  
  214          self.salt = salt
  215  
  216          if serializer is None:
  217              serializer = self.default_serializer
  218  
  219          self.serializer: _PDataSerializer[_TSerialized] = serializer
  220          self.is_text_serializer: bool = is_text_serializer(serializer)
  221  
  222          if signer is None:
  223              signer = self.default_signer
  224  
  225          self.signer: type[Signer] = signer
  226          self.signer_kwargs: dict[str, t.Any] = signer_kwargs or {}
  227  
  228          if fallback_signers is None:
  229              fallback_signers = list(self.default_fallback_signers)
  230  
  231          self.fallback_signers: list[
  232              dict[str, t.Any] | tuple[type[Signer], dict[str, t.Any]] | type[Signer]
  233          ] = fallback_signers
  234          self.serializer_kwargs: dict[str, t.Any] = serializer_kwargs or {}
  235  
  236      @property
  237      def secret_key(self) -> bytes:
  238          """The newest (last) entry in the :attr:`secret_keys` list. This
  239          is for compatibility from before key rotation support was added.
  240          """
  241          return self.secret_keys[-1]
  242  
  243      def load_payload(
  244          self, payload: bytes, serializer: _PDataSerializer[t.Any] | None = None
  245      ) -> t.Any:
  246          """Loads the encoded object. This function raises
  247          :class:`.BadPayload` if the payload is not valid. The
  248          ``serializer`` parameter can be used to override the serializer
  249          stored on the class. The encoded ``payload`` should always be
  250          bytes.
  251          """
  252          if serializer is None:
  253              use_serializer = self.serializer
  254              is_text = self.is_text_serializer
  255          else:
  256              use_serializer = serializer
  257              is_text = is_text_serializer(serializer)
  258  
  259          try:
  260              if is_text:
  261                  return use_serializer.loads(payload.decode("utf-8"))  # type: ignore[arg-type]
  262  
  263              return use_serializer.loads(payload)  # type: ignore[arg-type]
  264          except Exception as e:
  265              raise BadPayload(
  266                  "Could not load the payload because an exception"
  267                  " occurred on unserializing the data.",
  268                  original_error=e,
  269              ) from e
  270  
  271      def dump_payload(self, obj: t.Any) -> bytes:
  272          """Dumps the encoded object. The return value is always bytes.
  273          If the internal serializer returns text, the value will be
  274          encoded as UTF-8.
  275          """
  276          return want_bytes(self.serializer.dumps(obj, **self.serializer_kwargs))
  277  
  278      def make_signer(self, salt: str | bytes | None = None) -> Signer:
  279          """Creates a new instance of the signer to be used. The default
  280          implementation uses the :class:`.Signer` base class.
  281          """
  282          if salt is None:
  283              salt = self.salt
  284  
  285          return self.signer(self.secret_keys, salt=salt, **self.signer_kwargs)
  286  
  287      def iter_unsigners(self, salt: str | bytes | None = None) -> cabc.Iterator[Signer]:
  288          """Iterates over all signers to be tried for unsigning. Starts
  289          with the configured signer, then constructs each signer
  290          specified in ``fallback_signers``.
  291          """
  292          if salt is None:
  293              salt = self.salt
  294  
  295          yield self.make_signer(salt)
  296  
  297          for fallback in self.fallback_signers:
  298              if isinstance(fallback, dict):
  299                  kwargs = fallback
  300                  fallback = self.signer
  301              elif isinstance(fallback, tuple):
  302                  fallback, kwargs = fallback
  303              else:
  304                  kwargs = self.signer_kwargs
  305  
  306              for secret_key in self.secret_keys:
  307                  yield fallback(secret_key, salt=salt, **kwargs)
  308  
  309      def dumps(self, obj: t.Any, salt: str | bytes | None = None) -> _TSerialized:
  310          """Returns a signed string serialized with the internal
  311          serializer. The return value can be either a byte or unicode
  312          string depending on the format of the internal serializer.
  313          """
  314          payload = want_bytes(self.dump_payload(obj))
  315          rv = self.make_signer(salt).sign(payload)
  316  
  317          if self.is_text_serializer:
  318              return rv.decode("utf-8")  # type: ignore[return-value]
  319  
  320          return rv  # type: ignore[return-value]
  321  
  322      def dump(self, obj: t.Any, f: t.IO[t.Any], salt: str | bytes | None = None) -> None:
  323          """Like :meth:`dumps` but dumps into a file. The file handle has
  324          to be compatible with what the internal serializer expects.
  325          """
  326          f.write(self.dumps(obj, salt))
  327  
  328      def loads(
  329          self, s: str | bytes, salt: str | bytes | None = None, **kwargs: t.Any
  330      ) -> t.Any:
  331          """Reverse of :meth:`dumps`. Raises :exc:`.BadSignature` if the
  332          signature validation fails.
  333          """
  334          s = want_bytes(s)
  335          last_exception = None
  336  
  337          for signer in self.iter_unsigners(salt):
  338              try:
  339                  return self.load_payload(signer.unsign(s))
  340              except BadSignature as err:
  341                  last_exception = err
  342  
  343          raise t.cast(BadSignature, last_exception)
  344  
  345      def load(self, f: t.IO[t.Any], salt: str | bytes | None = None) -> t.Any:
  346          """Like :meth:`loads` but loads from a file."""
  347          return self.loads(f.read(), salt)
  348  
  349      def loads_unsafe(
  350          self, s: str | bytes, salt: str | bytes | None = None
  351      ) -> tuple[bool, t.Any]:
  352          """Like :meth:`loads` but without verifying the signature. This
  353          is potentially very dangerous to use depending on how your
  354          serializer works. The return value is ``(signature_valid,
  355          payload)`` instead of just the payload. The first item will be a
  356          boolean that indicates if the signature is valid. This function
  357          never fails.
  358  
  359          Use it for debugging only and if you know that your serializer
  360          module is not exploitable (for example, do not use it with a
  361          pickle serializer).
  362  
  363          .. versionadded:: 0.15
  364          """
  365          return self._loads_unsafe_impl(s, salt)
  366  
  367      def _loads_unsafe_impl(
  368          self,
  369          s: str | bytes,
  370          salt: str | bytes | None,
  371          load_kwargs: dict[str, t.Any] | None = None,
  372          load_payload_kwargs: dict[str, t.Any] | None = None,
  373      ) -> tuple[bool, t.Any]:
  374          """Low level helper function to implement :meth:`loads_unsafe`
  375          in serializer subclasses.
  376          """
  377          if load_kwargs is None:
  378              load_kwargs = {}
  379  
  380          try:
  381              return True, self.loads(s, salt=salt, **load_kwargs)
  382          except BadSignature as e:
  383              if e.payload is None:
  384                  return False, None
  385  
  386              if load_payload_kwargs is None:
  387                  load_payload_kwargs = {}
  388  
  389              try:
  390                  return (
  391                      False,
  392                      self.load_payload(e.payload, **load_payload_kwargs),
  393                  )
  394              except BadPayload:
  395                  return False, None
  396  
  397      def load_unsafe(
  398          self, f: t.IO[t.Any], salt: str | bytes | None = None
  399      ) -> tuple[bool, t.Any]:
  400          """Like :meth:`loads_unsafe` but loads from a file.
  401  
  402          .. versionadded:: 0.15
  403          """
  404          return self.loads_unsafe(f.read(), salt=salt)
</file>

<file path="src/itsdangerous/signer.py">
    1  from __future__ import annotations
    2  
    3  import collections.abc as cabc
    4  import hashlib
    5  import hmac
    6  import typing as t
    7  
    8  from .encoding import _base64_alphabet
    9  from .encoding import base64_decode
   10  from .encoding import base64_encode
   11  from .encoding import want_bytes
   12  from .exc import BadSignature
   13  
   14  
   15  class SigningAlgorithm:
   16      """Subclasses must implement :meth:`get_signature` to provide
   17      signature generation functionality.
   18      """
   19  
   20      def get_signature(self, key: bytes, value: bytes) -> bytes:
   21          """Returns the signature for the given key and value."""
   22          raise NotImplementedError()
   23  
   24      def verify_signature(self, key: bytes, value: bytes, sig: bytes) -> bool:
   25          """Verifies the given signature matches the expected
   26          signature.
   27          """
   28          return hmac.compare_digest(sig, self.get_signature(key, value))
   29  
   30  
   31  class NoneAlgorithm(SigningAlgorithm):
   32      """Provides an algorithm that does not perform any signing and
   33      returns an empty signature.
   34      """
   35  
   36      def get_signature(self, key: bytes, value: bytes) -> bytes:
   37          return b""
   38  
   39  
   40  def _lazy_sha1(string: bytes = b"") -> t.Any:
   41      """Don't access ``hashlib.sha1`` until runtime. FIPS builds may not include
   42      SHA-1, in which case the import and use as a default would fail before the
   43      developer can configure something else.
   44      """
   45      return hashlib.sha1(string)
   46  
   47  
   48  class HMACAlgorithm(SigningAlgorithm):
   49      """Provides signature generation using HMACs."""
   50  
   51      #: The digest method to use with the MAC algorithm. This defaults to
   52      #: SHA1, but can be changed to any other function in the hashlib
   53      #: module.
   54      default_digest_method: t.Any = staticmethod(_lazy_sha1)
   55  
   56      def __init__(self, digest_method: t.Any = None):
   57          if digest_method is None:
   58              digest_method = self.default_digest_method
   59  
   60          self.digest_method: t.Any = digest_method
   61  
   62      def get_signature(self, key: bytes, value: bytes) -> bytes:
   63          mac = hmac.new(key, msg=value, digestmod=self.digest_method)
   64          return mac.digest()
   65  
   66  
   67  def _make_keys_list(
   68      secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
   69  ) -> list[bytes]:
   70      if isinstance(secret_key, (str, bytes)):
   71          return [want_bytes(secret_key)]
   72  
   73      return [want_bytes(s) for s in secret_key]  # pyright: ignore
   74  
   75  
   76  class Signer:
   77      """A signer securely signs bytes, then unsigns them to verify that
   78      the value hasn't been changed.
   79  
   80      The secret key should be a random string of ``bytes`` and should not
   81      be saved to code or version control. Different salts should be used
   82      to distinguish signing in different contexts. See :doc:`/concepts`
   83      for information about the security of the secret key and salt.
   84  
   85      :param secret_key: The secret key to sign and verify with. Can be a
   86          list of keys, oldest to newest, to support key rotation.
   87      :param salt: Extra key to combine with ``secret_key`` to distinguish
   88          signatures in different contexts.
   89      :param sep: Separator between the signature and value.
   90      :param key_derivation: How to derive the signing key from the secret
   91          key and salt. Possible values are ``concat``, ``django-concat``,
   92          or ``hmac``. Defaults to :attr:`default_key_derivation`, which
   93          defaults to ``django-concat``.
   94      :param digest_method: Hash function to use when generating the HMAC
   95          signature. Defaults to :attr:`default_digest_method`, which
   96          defaults to :func:`hashlib.sha1`. Note that the security of the
   97          hash alone doesn't apply when used intermediately in HMAC.
   98      :param algorithm: A :class:`SigningAlgorithm` instance to use
   99          instead of building a default :class:`HMACAlgorithm` with the
  100          ``digest_method``.
  101  
  102      .. versionchanged:: 2.0
  103          Added support for key rotation by passing a list to
  104          ``secret_key``.
  105  
  106      .. versionchanged:: 0.18
  107          ``algorithm`` was added as an argument to the class constructor.
  108  
  109      .. versionchanged:: 0.14
  110          ``key_derivation`` and ``digest_method`` were added as arguments
  111          to the class constructor.
  112      """
  113  
  114      #: The default digest method to use for the signer. The default is
  115      #: :func:`hashlib.sha1`, but can be changed to any :mod:`hashlib` or
  116      #: compatible object. Note that the security of the hash alone
  117      #: doesn't apply when used intermediately in HMAC.
  118      #:
  119      #: .. versionadded:: 0.14
  120      default_digest_method: t.Any = staticmethod(_lazy_sha1)
  121  
  122      #: The default scheme to use to derive the signing key from the
  123      #: secret key and salt. The default is ``django-concat``. Possible
  124      #: values are ``concat``, ``django-concat``, and ``hmac``.
  125      #:
  126      #: .. versionadded:: 0.14
  127      default_key_derivation: str = "django-concat"
  128  
  129      def __init__(
  130          self,
  131          secret_key: str | bytes | cabc.Iterable[str] | cabc.Iterable[bytes],
  132          salt: str | bytes | None = b"itsdangerous.Signer",
  133          sep: str | bytes = b".",
  134          key_derivation: str | None = None,
  135          digest_method: t.Any | None = None,
  136          algorithm: SigningAlgorithm | None = None,
  137      ):
  138          #: The list of secret keys to try for verifying signatures, from
  139          #: oldest to newest. The newest (last) key is used for signing.
  140          #:
  141          #: This allows a key rotation system to keep a list of allowed
  142          #: keys and remove expired ones.
  143          self.secret_keys: list[bytes] = _make_keys_list(secret_key)
  144          self.sep: bytes = want_bytes(sep)
  145  
  146          if self.sep in _base64_alphabet:
  147              raise ValueError(
  148                  "The given separator cannot be used because it may be"
  149                  " contained in the signature itself. ASCII letters,"
  150                  " digits, and '-_=' must not be used."
  151              )
  152  
  153          if salt is not None:
  154              salt = want_bytes(salt)
  155          else:
  156              salt = b"itsdangerous.Signer"
  157  
  158          self.salt = salt
  159  
  160          if key_derivation is None:
  161              key_derivation = self.default_key_derivation
  162  
  163          self.key_derivation: str = key_derivation
  164  
  165          if digest_method is None:
  166              digest_method = self.default_digest_method
  167  
  168          self.digest_method: t.Any = digest_method
  169  
  170          if algorithm is None:
  171              algorithm = HMACAlgorithm(self.digest_method)
  172  
  173          self.algorithm: SigningAlgorithm = algorithm
  174  
  175      @property
  176      def secret_key(self) -> bytes:
  177          """The newest (last) entry in the :attr:`secret_keys` list. This
  178          is for compatibility from before key rotation support was added.
  179          """
  180          return self.secret_keys[-1]
  181  
  182      def derive_key(self, secret_key: str | bytes | None = None) -> bytes:
  183          """This method is called to derive the key. The default key
  184          derivation choices can be overridden here. Key derivation is not
  185          intended to be used as a security method to make a complex key
  186          out of a short password. Instead you should use large random
  187          secret keys.
  188  
  189          :param secret_key: A specific secret key to derive from.
  190              Defaults to the last item in :attr:`secret_keys`.
  191  
  192          .. versionchanged:: 2.0
  193              Added the ``secret_key`` parameter.
  194          """
  195          if secret_key is None:
  196              secret_key = self.secret_keys[-1]
  197          else:
  198              secret_key = want_bytes(secret_key)
  199  
  200          if self.key_derivation == "concat":
  201              return t.cast(bytes, self.digest_method(self.salt + secret_key).digest())
  202          elif self.key_derivation == "django-concat":
  203              return t.cast(
  204                  bytes, self.digest_method(self.salt + b"signer" + secret_key).digest()
  205              )
  206          elif self.key_derivation == "hmac":
  207              mac = hmac.new(secret_key, digestmod=self.digest_method)
  208              mac.update(self.salt)
  209              return mac.digest()
  210          elif self.key_derivation == "none":
  211              return secret_key
  212          else:
  213              raise TypeError("Unknown key derivation method")
  214  
  215      def get_signature(self, value: str | bytes) -> bytes:
  216          """Returns the signature for the given value."""
  217          value = want_bytes(value)
  218          key = self.derive_key()
  219          sig = self.algorithm.get_signature(key, value)
  220          return base64_encode(sig)
  221  
  222      def sign(self, value: str | bytes) -> bytes:
  223          """Signs the given string."""
  224          value = want_bytes(value)
  225          return value + self.sep + self.get_signature(value)
  226  
  227      def verify_signature(self, value: str | bytes, sig: str | bytes) -> bool:
  228          """Verifies the signature for the given value."""
  229          try:
  230              sig = base64_decode(sig)
  231          except Exception:
  232              return False
  233  
  234          value = want_bytes(value)
  235  
  236          for secret_key in reversed(self.secret_keys):
  237              key = self.derive_key(secret_key)
  238  
  239              if self.algorithm.verify_signature(key, value, sig):
  240                  return True
  241  
  242          return False
  243  
  244      def unsign(self, signed_value: str | bytes) -> bytes:
  245          """Unsigns the given string."""
  246          signed_value = want_bytes(signed_value)
  247  
  248          if self.sep not in signed_value:
  249              raise BadSignature(f"No {self.sep!r} found in value")
  250  
  251          value, sig = signed_value.rsplit(self.sep, 1)
  252  
  253          if self.verify_signature(value, sig):
  254              return value
  255  
  256          raise BadSignature(f"Signature {sig!r} does not match", payload=value)
  257  
  258      def validate(self, signed_value: str | bytes) -> bool:
  259          """Only validates the given signed value. Returns ``True`` if
  260          the signature exists and is valid.
  261          """
  262          try:
  263              self.unsign(signed_value)
  264              return True
  265          except BadSignature:
  266              return False
</file>

<file path="src/itsdangerous/timed.py">
    1  from __future__ import annotations
    2  
    3  import collections.abc as cabc
    4  import time
    5  import typing as t
    6  from datetime import datetime
    7  from datetime import timezone
    8  
    9  from .encoding import base64_decode
   10  from .encoding import base64_encode
   11  from .encoding import bytes_to_int
   12  from .encoding import int_to_bytes
   13  from .encoding import want_bytes
   14  from .exc import BadSignature
   15  from .exc import BadTimeSignature
   16  from .exc import SignatureExpired
   17  from .serializer import _TSerialized
   18  from .serializer import Serializer
   19  from .signer import Signer
   20  
   21  
   22  class TimestampSigner(Signer):
   23      """Works like the regular :class:`.Signer` but also records the time
   24      of the signing and can be used to expire signatures. The
   25      :meth:`unsign` method can raise :exc:`.SignatureExpired` if the
   26      unsigning failed because the signature is expired.
   27      """
   28  
   29      def get_timestamp(self) -> int:
   30          """Returns the current timestamp. The function must return an
   31          integer.
   32          """
   33          return int(time.time())
   34  
   35      def timestamp_to_datetime(self, ts: int) -> datetime:
   36          """Convert the timestamp from :meth:`get_timestamp` into an
   37          aware :class`datetime.datetime` in UTC.
   38  
   39          .. versionchanged:: 2.0
   40              The timestamp is returned as a timezone-aware ``datetime``
   41              in UTC rather than a naive ``datetime`` assumed to be UTC.
   42          """
   43          return datetime.fromtimestamp(ts, tz=timezone.utc)
   44  
   45      def sign(self, value: str | bytes) -> bytes:
   46          """Signs the given string and also attaches time information."""
   47          value = want_bytes(value)
   48          timestamp = base64_encode(int_to_bytes(self.get_timestamp()))
   49          sep = want_bytes(self.sep)
   50          value = value + sep + timestamp
   51          return value + sep + self.get_signature(value)
   52  
   53      # Ignore overlapping signatures check, return_timestamp is the only
   54      # parameter that affects the return type.
   55  
   56      @t.overload
   57      def unsign(  # pyright: ignore
   58          self,
   59          signed_value: str | bytes,
   60          max_age: int | None = None,
   61          return_timestamp: t.Literal[False] = False,
   62      ) -> bytes: ...
   63  
   64      @t.overload
   65      def unsign(
   66          self,
   67          signed_value: str | bytes,
   68          max_age: int | None = None,
   69          return_timestamp: t.Literal[True] = True,
   70      ) -> tuple[bytes, datetime]: ...
   71  
   72      def unsign(
   73          self,
   74          signed_value: str | bytes,
   75          max_age: int | None = None,
   76          return_timestamp: bool = False,
   77      ) -> tuple[bytes, datetime] | bytes:
   78          """Works like the regular :meth:`.Signer.unsign` but can also
   79          validate the time. See the base docstring of the class for
   80          the general behavior. If ``return_timestamp`` is ``True`` the
   81          timestamp of the signature will be returned as an aware
   82          :class:`datetime.datetime` object in UTC.
   83  
   84          .. versionchanged:: 2.0
   85              The timestamp is returned as a timezone-aware ``datetime``
   86              in UTC rather than a naive ``datetime`` assumed to be UTC.
   87          """
   88          try:
   89              result = super().unsign(signed_value)
   90              sig_error = None
   91          except BadSignature as e:
   92              sig_error = e
   93              result = e.payload or b""
   94  
   95          sep = want_bytes(self.sep)
   96  
   97          # If there is no timestamp in the result there is something
   98          # seriously wrong. In case there was a signature error, we raise
   99          # that one directly, otherwise we have a weird situation in
  100          # which we shouldn't have come except someone uses a time-based
  101          # serializer on non-timestamp data, so catch that.
  102          if sep not in result:
  103              if sig_error:
  104                  raise sig_error
  105  
  106              raise BadTimeSignature("timestamp missing", payload=result)
  107  
  108          value, ts_bytes = result.rsplit(sep, 1)
  109          ts_int: int | None = None
  110          ts_dt: datetime | None = None
  111  
  112          try:
  113              ts_int = bytes_to_int(base64_decode(ts_bytes))
  114          except Exception:
  115              pass
  116  
  117          # Signature is *not* okay. Raise a proper error now that we have
  118          # split the value and the timestamp.
  119          if sig_error is not None:
  120              if ts_int is not None:
  121                  try:
  122                      ts_dt = self.timestamp_to_datetime(ts_int)
  123                  except (ValueError, OSError, OverflowError) as exc:
  124                      # Windows raises OSError
  125                      # 32-bit raises OverflowError
  126                      raise BadTimeSignature(
  127                          "Malformed timestamp", payload=value
  128                      ) from exc
  129  
  130              raise BadTimeSignature(str(sig_error), payload=value, date_signed=ts_dt)
  131  
  132          # Signature was okay but the timestamp is actually not there or
  133          # malformed. Should not happen, but we handle it anyway.
  134          if ts_int is None:
  135              raise BadTimeSignature("Malformed timestamp", payload=value)
  136  
  137          # Check timestamp is not older than max_age
  138          if max_age is not None:
  139              age = self.get_timestamp() - ts_int
  140  
  141              if age > max_age:
  142                  raise SignatureExpired(
  143                      f"Signature age {age} > {max_age} seconds",
  144                      payload=value,
  145                      date_signed=self.timestamp_to_datetime(ts_int),
  146                  )
  147  
  148              if age < 0:
  149                  raise SignatureExpired(
  150                      f"Signature age {age} < 0 seconds",
  151                      payload=value,
  152                      date_signed=self.timestamp_to_datetime(ts_int),
  153                  )
  154  
  155          if return_timestamp:
  156              return value, self.timestamp_to_datetime(ts_int)
  157  
  158          return value
  159  
  160      def validate(self, signed_value: str | bytes, max_age: int | None = None) -> bool:
  161          """Only validates the given signed value. Returns ``True`` if
  162          the signature exists and is valid."""
  163          try:
  164              self.unsign(signed_value, max_age=max_age)
  165              return True
  166          except BadSignature:
  167              return False
  168  
  169  
  170  class TimedSerializer(Serializer[_TSerialized]):
  171      """Uses :class:`TimestampSigner` instead of the default
  172      :class:`.Signer`.
  173      """
  174  
  175      default_signer: type[TimestampSigner] = TimestampSigner  # pyright: ignore
  176  
  177      def iter_unsigners(
  178          self, salt: str | bytes | None = None
  179      ) -> cabc.Iterator[TimestampSigner]:
  180          return t.cast("cabc.Iterator[TimestampSigner]", super().iter_unsigners(salt))
  181  
  182      # TODO: Signature is incompatible because parameters were added
  183      #  before salt.
  184  
  185      def loads(  # type: ignore[override]
  186          self,
  187          s: str | bytes,
  188          max_age: int | None = None,
  189          return_timestamp: bool = False,
  190          salt: str | bytes | None = None,
  191      ) -> t.Any:
  192          """Reverse of :meth:`dumps`, raises :exc:`.BadSignature` if the
  193          signature validation fails. If a ``max_age`` is provided it will
  194          ensure the signature is not older than that time in seconds. In
  195          case the signature is outdated, :exc:`.SignatureExpired` is
  196          raised. All arguments are forwarded to the signer's
  197          :meth:`~TimestampSigner.unsign` method.
  198          """
  199          s = want_bytes(s)
  200          last_exception = None
  201  
  202          for signer in self.iter_unsigners(salt):
  203              try:
  204                  base64d, timestamp = signer.unsign(
  205                      s, max_age=max_age, return_timestamp=True
  206                  )
  207                  payload = self.load_payload(base64d)
  208  
  209                  if return_timestamp:
  210                      return payload, timestamp
  211  
  212                  return payload
  213              except SignatureExpired:
  214                  # The signature was unsigned successfully but was
  215                  # expired. Do not try the next signer.
  216                  raise
  217              except BadSignature as err:
  218                  last_exception = err
  219  
  220          raise t.cast(BadSignature, last_exception)
  221  
  222      def loads_unsafe(  # type: ignore[override]
  223          self,
  224          s: str | bytes,
  225          max_age: int | None = None,
  226          salt: str | bytes | None = None,
  227      ) -> tuple[bool, t.Any]:
  228          return self._loads_unsafe_impl(s, salt, load_kwargs={"max_age": max_age})
</file>

<file path="src/itsdangerous/url_safe.py">
    1  from __future__ import annotations
    2  
    3  import typing as t
    4  import zlib
    5  
    6  from ._json import _CompactJSON
    7  from .encoding import base64_decode
    8  from .encoding import base64_encode
    9  from .exc import BadPayload
   10  from .serializer import _PDataSerializer
   11  from .serializer import Serializer
   12  from .timed import TimedSerializer
   13  
   14  
   15  class URLSafeSerializerMixin(Serializer[str]):
   16      """Mixed in with a regular serializer it will attempt to zlib
   17      compress the string to make it shorter if necessary. It will also
   18      base64 encode the string so that it can safely be placed in a URL.
   19      """
   20  
   21      default_serializer: _PDataSerializer[str] = _CompactJSON
   22  
   23      def load_payload(
   24          self,
   25          payload: bytes,
   26          *args: t.Any,
   27          serializer: t.Any | None = None,
   28          **kwargs: t.Any,
   29      ) -> t.Any:
   30          decompress = False
   31  
   32          if payload.startswith(b"."):
   33              payload = payload[1:]
   34              decompress = True
   35  
   36          try:
   37              json = base64_decode(payload)
   38          except Exception as e:
   39              raise BadPayload(
   40                  "Could not base64 decode the payload because of an exception",
   41                  original_error=e,
   42              ) from e
   43  
   44          if decompress:
   45              try:
   46                  json = zlib.decompress(json)
   47              except Exception as e:
   48                  raise BadPayload(
   49                      "Could not zlib decompress the payload before decoding the payload",
   50                      original_error=e,
   51                  ) from e
   52  
   53          return super().load_payload(json, *args, **kwargs)
   54  
   55      def dump_payload(self, obj: t.Any) -> bytes:
   56          json = super().dump_payload(obj)
   57          is_compressed = False
   58          compressed = zlib.compress(json)
   59  
   60          if len(compressed) < (len(json) - 1):
   61              json = compressed
   62              is_compressed = True
   63  
   64          base64d = base64_encode(json)
   65  
   66          if is_compressed:
   67              base64d = b"." + base64d
   68  
   69          return base64d
   70  
   71  
   72  class URLSafeSerializer(URLSafeSerializerMixin, Serializer[str]):
   73      """Works like :class:`.Serializer` but dumps and loads into a URL
   74      safe string consisting of the upper and lowercase character of the
   75      alphabet as well as ``'_'``, ``'-'`` and ``'.'``.
   76      """
   77  
   78  
   79  class URLSafeTimedSerializer(URLSafeSerializerMixin, TimedSerializer[str]):
   80      """Works like :class:`.TimedSerializer` but dumps and loads into a
   81      URL safe string consisting of the upper and lowercase character of
   82      the alphabet as well as ``'_'``, ``'-'`` and ``'.'``.
   83      """
</file>

<file path="tests/test_itsdangerous/__init__.py">

</file>

<file path="tests/test_itsdangerous/test_encoding.py">
    1  import pytest
    2  
    3  from itsdangerous.encoding import base64_decode
    4  from itsdangerous.encoding import base64_encode
    5  from itsdangerous.encoding import bytes_to_int
    6  from itsdangerous.encoding import int_to_bytes
    7  from itsdangerous.encoding import want_bytes
    8  from itsdangerous.exc import BadData
    9  
   10  
   11  @pytest.mark.parametrize("value", ("mañana", b"tomorrow"))
   12  def test_want_bytes(value):
   13      out = want_bytes(value)
   14      assert isinstance(out, bytes)
   15  
   16  
   17  @pytest.mark.parametrize("value", ("無限", b"infinite"))
   18  def test_base64(value):
   19      enc = base64_encode(value)
   20      assert isinstance(enc, bytes)
   21      dec = base64_decode(enc)
   22      assert dec == want_bytes(value)
   23  
   24  
   25  def test_base64_bad():
   26      with pytest.raises(BadData):
   27          base64_decode("12345")
   28  
   29  
   30  @pytest.mark.parametrize(
   31      ("value", "expect"), ((0, b""), (192, b"\xc0"), (18446744073709551615, b"\xff" * 8))
   32  )
   33  def test_int_bytes(value, expect):
   34      enc = int_to_bytes(value)
   35      assert enc == expect
   36      dec = bytes_to_int(enc)
   37      assert dec == value
</file>

<file path="tests/test_itsdangerous/test_serializer.py">
    1  import hashlib
    2  import pickle
    3  from functools import partial
    4  from io import BytesIO
    5  from io import StringIO
    6  from typing import Any
    7  from typing import cast
    8  from typing import IO
    9  from typing import overload
   10  
   11  import pytest
   12  
   13  from itsdangerous.exc import BadPayload
   14  from itsdangerous.exc import BadSignature
   15  from itsdangerous.serializer import Serializer
   16  from itsdangerous.signer import _lazy_sha1
   17  from itsdangerous.signer import Signer
   18  
   19  
   20  @overload
   21  def coerce_str(ref: str, s: str) -> str: ...
   22  
   23  
   24  @overload
   25  def coerce_str(ref: bytes, s: str) -> bytes: ...
   26  
   27  
   28  def coerce_str(ref: str | bytes, s: str) -> str | bytes:
   29      if isinstance(ref, bytes):
   30          return s.encode("utf8")
   31  
   32      return s
   33  
   34  
   35  class TestSerializer:
   36      @pytest.fixture(params=(Serializer, partial(Serializer, serializer=pickle)))
   37      def serializer_factory(self, request):
   38          return partial(request.param, secret_key="secret_key")
   39  
   40      @pytest.fixture()
   41      def serializer(self, serializer_factory):
   42          return serializer_factory()
   43  
   44      @pytest.fixture()
   45      def value(self):
   46          return {"id": 42}
   47  
   48      @pytest.mark.parametrize(
   49          "value", (None, True, "str", "text", [1, 2, 3], {"id": 42})
   50      )
   51      def test_serializer(self, serializer: Serializer, value: Any):
   52          assert serializer.loads(serializer.dumps(value)) == value
   53  
   54      @pytest.mark.parametrize(
   55          "transform",
   56          (
   57              lambda s: s.upper(),
   58              lambda s: s + coerce_str(s, "a"),
   59              lambda s: coerce_str(s, "a") + s[1:],
   60              lambda s: s.replace(coerce_str(s, "."), coerce_str(s, "")),
   61          ),
   62      )
   63      def test_changed_value(self, serializer: Serializer, value: Any, transform):
   64          signed = serializer.dumps(value)
   65          assert serializer.loads(signed) == value
   66          changed = transform(signed)
   67  
   68          with pytest.raises(BadSignature):
   69              serializer.loads(changed)
   70  
   71      def test_bad_signature_exception(self, serializer: Serializer, value: Any):
   72          bad_signed = serializer.dumps(value)[:-1]
   73  
   74          with pytest.raises(BadSignature) as exc_info:
   75              serializer.loads(bad_signed)
   76  
   77          payload = cast(bytes, exc_info.value.payload)
   78          assert serializer.load_payload(payload) == value
   79  
   80      def test_bad_payload_exception(self, serializer: Serializer, value: Any):
   81          original = serializer.dumps(value)
   82          payload = original.rsplit(coerce_str(original, "."), 1)[0]  # type: ignore
   83          bad = serializer.make_signer().sign(payload[:-1])
   84  
   85          with pytest.raises(BadPayload) as exc_info:
   86              serializer.loads(bad)
   87  
   88          assert exc_info.value.original_error is not None
   89  
   90      def test_loads_unsafe(self, serializer: Serializer, value: Any):
   91          signed = serializer.dumps(value)
   92          assert serializer.loads_unsafe(signed) == (True, value)
   93  
   94          bad_signed = signed[:-1]
   95          assert serializer.loads_unsafe(bad_signed) == (False, value)
   96  
   97          payload = signed.rsplit(coerce_str(signed, "."), 1)[0]  # type: ignore
   98          bad_payload = serializer.make_signer().sign(payload[:-1])[:-1]
   99          assert serializer.loads_unsafe(bad_payload) == (False, None)
  100  
  101          class BadUnsign(serializer.signer):  # type: ignore
  102              def unsign(self, signed_value, *args, **kwargs):
  103                  try:
  104                      return super().unsign(signed_value, *args, **kwargs)
  105                  except BadSignature as e:
  106                      e.payload = None
  107                      raise
  108  
  109          serializer.signer = BadUnsign
  110          assert serializer.loads_unsafe(bad_signed) == (False, None)
  111  
  112      def test_file(self, serializer: Serializer, value: Any):
  113          f = cast(
  114              IO, BytesIO() if isinstance(serializer.dumps(value), bytes) else StringIO()
  115          )
  116          serializer.dump(value, f)
  117          f.seek(0)
  118          assert serializer.load(f) == value
  119          f.seek(0)
  120          assert serializer.load_unsafe(f) == (True, value)
  121  
  122      def test_alt_salt(self, serializer: Serializer, value: Any):
  123          signed = serializer.dumps(value, salt="other")
  124  
  125          with pytest.raises(BadSignature):
  126              serializer.loads(signed)
  127  
  128          assert serializer.loads(signed, salt="other") == value
  129  
  130      def test_signer_cls(self, serializer_factory, serializer: Serializer, value: Any):
  131          class Other(serializer.signer):  # type: ignore
  132              default_key_derivation = "hmac"
  133  
  134          other = serializer_factory(signer=Other)
  135          assert other.loads(other.dumps(value)) == value
  136          assert other.dumps(value) != serializer.dumps(value)
  137  
  138      def test_signer_kwargs(
  139          self, serializer_factory, serializer: Serializer, value: Any
  140      ):
  141          other = serializer_factory(signer_kwargs={"key_derivation": "hmac"})
  142          assert other.loads(other.dumps(value)) == value
  143          assert other.dumps("value") != serializer.dumps("value")
  144  
  145      def test_serializer_kwargs(self, serializer_factory):
  146          serializer = serializer_factory(serializer_kwargs={"skipkeys": True})
  147  
  148          try:
  149              serializer.serializer.dumps(None, skipkeys=True)
  150          except TypeError:
  151              return
  152  
  153          assert serializer.loads(serializer.dumps({(): 1})) == {}
  154  
  155      def test_fallback_signers(self, serializer_factory, value: Any):
  156          serializer = serializer_factory(signer_kwargs={"digest_method": hashlib.sha256})
  157          signed = serializer.dumps(value)
  158  
  159          fallback_serializer = serializer_factory(
  160              signer_kwargs={"digest_method": hashlib.sha1},
  161              fallback_signers=[{"digest_method": hashlib.sha256}],
  162          )
  163  
  164          assert fallback_serializer.loads(signed) == value
  165  
  166      def test_iter_unsigners(self, serializer: Serializer, serializer_factory):
  167          class Signer256(serializer.signer):  # type: ignore
  168              default_digest_method = hashlib.sha256
  169  
  170          serializer = serializer_factory(
  171              secret_key="secret_key",
  172              fallback_signers=[
  173                  {"digest_method": hashlib.sha256},
  174                  (Signer, {"digest_method": hashlib.sha256}),
  175                  Signer256,
  176              ],
  177          )
  178  
  179          unsigners = serializer.iter_unsigners()
  180          assert next(unsigners).digest_method == _lazy_sha1
  181  
  182          for signer in unsigners:
  183              assert signer.digest_method == hashlib.sha256
  184  
  185  
  186  def test_digests():
  187      factory = partial(Serializer, secret_key="dev key", salt="dev salt")
  188      default_value = factory(signer_kwargs={}).dumps([42])
  189      sha1_value = factory(signer_kwargs={"digest_method": hashlib.sha1}).dumps([42])
  190      sha512_value = factory(signer_kwargs={"digest_method": hashlib.sha512}).dumps([42])
  191      assert default_value == sha1_value
  192      assert sha1_value == "[42].-9cNi0CxsSB3hZPNCe9a2eEs1ZM"
  193      assert sha512_value == (
  194          "[42].MKCz_0nXQqv7wKpfHZcRtJRmpT2T5uvs9YQsJEhJimqxc"
  195          "9bCLxG31QzS5uC8OVBI1i6jyOLAFNoKaF5ckO9L5Q"
  196      )
</file>

<file path="tests/test_itsdangerous/test_signer.py">
    1  import hashlib
    2  from functools import partial
    3  
    4  import pytest
    5  
    6  from itsdangerous.exc import BadSignature
    7  from itsdangerous.signer import HMACAlgorithm
    8  from itsdangerous.signer import NoneAlgorithm
    9  from itsdangerous.signer import Signer
   10  from itsdangerous.signer import SigningAlgorithm
   11  
   12  
   13  class _ReverseAlgorithm(SigningAlgorithm):
   14      def get_signature(self, key, value):
   15          return (key + value)[::-1]
   16  
   17  
   18  class TestSigner:
   19      @pytest.fixture()
   20      def signer_factory(self):
   21          return partial(Signer, secret_key="secret-key")
   22  
   23      @pytest.fixture()
   24      def signer(self, signer_factory):
   25          return signer_factory()
   26  
   27      def test_signer(self, signer):
   28          signed = signer.sign("my string")
   29          assert isinstance(signed, bytes)
   30          assert signer.validate(signed)
   31          out = signer.unsign(signed)
   32          assert out == b"my string"
   33  
   34      def test_no_separator(self, signer):
   35          signed = signer.sign("my string")
   36          signed = signed.replace(signer.sep, b"*", 1)
   37          assert not signer.validate(signed)
   38  
   39          with pytest.raises(BadSignature):
   40              signer.unsign(signed)
   41  
   42      def test_broken_signature(self, signer):
   43          signed = signer.sign("b")
   44          bad_signed = signed[:-1]
   45          bad_sig = bad_signed.rsplit(b".", 1)[1]
   46          assert not signer.verify_signature(b"b", bad_sig)
   47  
   48          with pytest.raises(BadSignature) as exc_info:
   49              signer.unsign(bad_signed)
   50  
   51          assert exc_info.value.payload == b"b"
   52  
   53      def test_changed_value(self, signer):
   54          signed = signer.sign("my string")
   55          signed = signed.replace(b"my", b"other", 1)
   56          assert not signer.validate(signed)
   57  
   58          with pytest.raises(BadSignature):
   59              signer.unsign(signed)
   60  
   61      def test_invalid_separator(self, signer_factory):
   62          with pytest.raises(ValueError) as exc_info:
   63              signer_factory(sep="-")
   64  
   65          assert "separator cannot be used" in str(exc_info.value)
   66  
   67      @pytest.mark.parametrize(
   68          "key_derivation", ("concat", "django-concat", "hmac", "none")
   69      )
   70      def test_key_derivation(self, signer_factory, key_derivation):
   71          signer = signer_factory(key_derivation=key_derivation)
   72          assert signer.unsign(signer.sign("value")) == b"value"
   73  
   74      def test_invalid_key_derivation(self, signer_factory):
   75          signer = signer_factory(key_derivation="invalid")
   76  
   77          with pytest.raises(TypeError):
   78              signer.derive_key()
   79  
   80      def test_digest_method(self, signer_factory):
   81          signer = signer_factory(digest_method=hashlib.md5)
   82          assert signer.unsign(signer.sign("value")) == b"value"
   83  
   84      @pytest.mark.parametrize(
   85          "algorithm", (None, NoneAlgorithm(), HMACAlgorithm(), _ReverseAlgorithm())
   86      )
   87      def test_algorithm(self, signer_factory, algorithm):
   88          signer = signer_factory(algorithm=algorithm)
   89          assert signer.unsign(signer.sign("value")) == b"value"
   90  
   91          if algorithm is None:
   92              assert signer.algorithm.digest_method == signer.digest_method
   93  
   94      def test_secret_keys(self):
   95          signer = Signer("a")
   96          signed = signer.sign("my string")
   97          assert isinstance(signed, bytes)
   98  
   99          signer = Signer(["a", "b"])
  100          assert signer.validate(signed)
  101          out = signer.unsign(signed)
  102          assert out == b"my string"
  103  
  104  
  105  def test_abstract_algorithm():
  106      alg = SigningAlgorithm()
  107  
  108      with pytest.raises(NotImplementedError):
  109          alg.get_signature(b"a", b"b")
</file>

<file path="tests/test_itsdangerous/test_timed.py">
    1  from datetime import datetime
    2  from datetime import timedelta
    3  from datetime import timezone
    4  from functools import partial
    5  
    6  import pytest
    7  from freezegun import freeze_time
    8  
    9  from itsdangerous.exc import BadTimeSignature
   10  from itsdangerous.exc import SignatureExpired
   11  from itsdangerous.signer import Signer
   12  from itsdangerous.timed import TimedSerializer
   13  from itsdangerous.timed import TimestampSigner
   14  from test_itsdangerous.test_serializer import TestSerializer
   15  from test_itsdangerous.test_signer import TestSigner
   16  
   17  
   18  class FreezeMixin:
   19      @pytest.fixture()
   20      def ts(self):
   21          return datetime(2011, 6, 24, 0, 9, 5, tzinfo=timezone.utc)
   22  
   23      @pytest.fixture(autouse=True)
   24      def freeze(self, ts):
   25          with freeze_time(ts) as ft:
   26              yield ft
   27  
   28  
   29  class TestTimestampSigner(FreezeMixin, TestSigner):
   30      @pytest.fixture()
   31      def signer_factory(self):
   32          return partial(TimestampSigner, secret_key="secret-key")
   33  
   34      def test_max_age(self, signer, ts, freeze):
   35          signed = signer.sign("value")
   36          freeze.tick()
   37          assert signer.unsign(signed, max_age=10) == b"value"
   38          freeze.tick(timedelta(seconds=10))
   39  
   40          with pytest.raises(SignatureExpired) as exc_info:
   41              signer.unsign(signed, max_age=10)
   42  
   43          assert exc_info.value.date_signed == ts
   44  
   45      def test_return_timestamp(self, signer, ts):
   46          signed = signer.sign("value")
   47          assert signer.unsign(signed, return_timestamp=True) == (b"value", ts)
   48  
   49      def test_timestamp_missing(self, signer):
   50          other = Signer("secret-key")
   51          signed = other.sign("value")
   52  
   53          with pytest.raises(BadTimeSignature) as exc_info:
   54              signer.unsign(signed)
   55  
   56          assert "missing" in str(exc_info.value)
   57          assert exc_info.value.date_signed is None
   58  
   59      def test_malformed_timestamp(self, signer):
   60          other = Signer("secret-key")
   61          signed = other.sign(b"value.____________")
   62  
   63          with pytest.raises(BadTimeSignature) as exc_info:
   64              signer.unsign(signed)
   65  
   66          assert "Malformed" in str(exc_info.value)
   67          assert exc_info.value.date_signed is None
   68  
   69      def test_malformed_future_timestamp(self, signer):
   70          signed = b"value.TgPVoaGhoQ.AGBfQ6G6cr07byTRt0zAdPljHOY"
   71  
   72          with pytest.raises(BadTimeSignature) as exc_info:
   73              signer.unsign(signed)
   74  
   75          assert "Malformed" in str(exc_info.value)
   76          assert exc_info.value.date_signed is None
   77  
   78      def test_future_age(self, signer):
   79          signed = signer.sign("value")
   80  
   81          with freeze_time("1971-05-31"):
   82              with pytest.raises(SignatureExpired) as exc_info:
   83                  signer.unsign(signed, max_age=10)
   84  
   85          assert isinstance(exc_info.value.date_signed, datetime)
   86  
   87      def test_sig_error_date_signed(self, signer):
   88          signed = signer.sign("my string").replace(b"my", b"other", 1)
   89  
   90          with pytest.raises(BadTimeSignature) as exc_info:
   91              signer.unsign(signed)
   92  
   93          assert isinstance(exc_info.value.date_signed, datetime)
   94  
   95  
   96  class TestTimedSerializer(FreezeMixin, TestSerializer):
   97      @pytest.fixture()
   98      def serializer_factory(self):
   99          return partial(TimedSerializer, secret_key="secret_key")
  100  
  101      def test_max_age(self, serializer, value, ts, freeze):
  102          signed = serializer.dumps(value)
  103          freeze.tick()
  104          assert serializer.loads(signed, max_age=10) == value
  105          freeze.tick(timedelta(seconds=10))
  106  
  107          with pytest.raises(SignatureExpired) as exc_info:
  108              serializer.loads(signed, max_age=10)
  109  
  110          assert exc_info.value.date_signed == ts
  111          assert serializer.load_payload(exc_info.value.payload) == value
  112  
  113      def test_return_payload(self, serializer, value, ts):
  114          signed = serializer.dumps(value)
  115          assert serializer.loads(signed, return_timestamp=True) == (value, ts)
</file>

<file path="tests/test_itsdangerous/test_url_safe.py">
    1  from functools import partial
    2  
    3  import pytest
    4  
    5  from itsdangerous.url_safe import URLSafeSerializer
    6  from itsdangerous.url_safe import URLSafeTimedSerializer
    7  from test_itsdangerous.test_serializer import TestSerializer
    8  from test_itsdangerous.test_timed import TestTimedSerializer
    9  
   10  
   11  class TestURLSafeSerializer(TestSerializer):
   12      @pytest.fixture()
   13      def serializer_factory(self):
   14          return partial(URLSafeSerializer, secret_key="secret-key")
   15  
   16      @pytest.fixture(params=({"id": 42}, pytest.param("a" * 1000, id="zlib")))
   17      def value(self, request):
   18          return request.param
   19  
   20  
   21  class TestURLSafeTimedSerializer(TestURLSafeSerializer, TestTimedSerializer):
   22      @pytest.fixture()
   23      def serializer_factory(self):
   24          return partial(URLSafeTimedSerializer, secret_key="secret-key")
</file>

Plan the story.
