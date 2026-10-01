# Chapter 2 · An Object That Writes Its Own HTML, and a Template That Escapes Its Arguments

> **Enters as:** `User(3, 'Alice "The <b>Great</b>"')` — an object with its own HTML; and the template text `'<p>User: {user:link} said: {comment}</p>'`

The escaped comment steps aside for a moment. It is about to be a field in somebody else's render, and before that can happen two other values have to be built: the user, and the template they will both be poured into.

## The third door: an object that claims to know its own markup

`escape(user)` enters the same three-branch hallway as before. The first door, `type(s) is str`, is shut — a `User` is not a `str`. The second opens: `hasattr(s, "__html__")` is true, so `escape` calls the method and wraps whatever comes back in `Markup`, with no escaping at all ([`__init__.py#L42-L43`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L42-L43)).

That is the whole protocol. An object that defines `__html__` is believed. This particular `User` deserves it — its `__html__` builds the span by calling `.format()` on a `Markup` literal, so the name goes through the escaping machinery on the way in (that render is the next chapter's business). The result comes back as `Markup('<span class="user">Alice &#34;The &lt;b&gt;Great&lt;/b&gt;&#34;</span>')`: the `<span>` tags intact and live, the double quotes and angle brackets *inside* the name turned into `&#34;` and `&lt;b&gt;`. The scenario prints it, and `__repr__` ([`__init__.py#L167-L168`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L167-L168)) shows the two kinds of bracket side by side in one value — that is the whole point of the library in a single line of output.

Had `__html__` instead returned `f'<span>{self.name}</span>'` with no escaping, `escape` would have wrapped that too, just as cheerfully, and the `<b>` would have been live markup. The documentation states the division of responsibility outright ([`docs/html.rst#L31-L43`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/docs/html.rst#L31-L43)): since `__html__` bypasses escaping, the author must escape user-provided data inside it.

> **For the owner:** `__html__` is the second unguarded door, after `Markup()` itself. Any class in your codebase — or in a dependency — that defines `__html__` has opted its output out of escaping everywhere it is used. It is worth enumerating them; each one is a small sanitizer written by hand. One guarantee you do get: an exception raised inside `__html__` propagates out of `escape` rather than being swallowed or crashing the interpreter. That was a real segfault in the C path once, and it is pinned by a test today ([`tests/test_exception_custom_html.py#L13-L23`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/tests/test_exception_custom_html.py#L13-L23)).

## The template: trusted because a developer typed it

Next, `Markup("<p>User: {user:link} said: {comment}</p>")` — the same no-op constructor from chapter 1 ([`__init__.py#L122-L131`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L122-L131)), here used for exactly what it is for: text the author controls. The `<p>` tags need to stay live, so the template must not be escaped. Everything substituted *into* it will be.

> **For the owner:** The asymmetry is worth naming before you sign off on a template layer. The literal text is trusted wholesale; only the field values are escaped. `Markup(some_template_from_the_database).format(...)` therefore protects the arguments and nothing else — the template itself can contain any markup it likes. If templates are ever user-supplied or user-editable in your system, MarkupSafe is not the control that makes that safe.

## `Markup.format`: standard parsing, custom field rendering

`template.format(user=user, comment=safe_comment)` does two things ([`__init__.py#L313-L315`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L313-L315)). It constructs a fresh `EscapeFormatter`, passing `self.escape` — the bound classmethod of the *actual* class, which is why a `Markup` subclass formats into its own type rather than decaying to `Markup`. The formatter stores that callable and chains to `string.Formatter.__init__` ([`__init__.py#L335-L337`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L335-L337)); the trace records it arriving as `escape=<bound method Markup.escape of <class 'markupsafe.Markup'>>`. Then it hands the whole job to `vformat`.

Everything about *parsing* `{user:link}` — finding the field names, splitting off the spec, walking `{0[1][bar]}`-style lookups — is the standard library's, unmodified. MarkupSafe overrides exactly one hook: `format_field`. That is a deliberate narrow seam. The only thing it wants to change is what happens to each value once it has been located.

A quick note on a road this run never takes: the `%` operator goes somewhere else entirely. `Markup.__mod__` wraps each argument in a `_MarkupEscapeHelper` ([`__init__.py#L154-L165`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L154-L165)), a tiny proxy that escapes lazily when `str()` or `repr()` is called on it but passes `__int__` and `__float__` straight through unescaped ([`__init__.py#L357-L379`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L357-L379)) — different mechanism, same guarantee, which is why `Markup("%i") % 3.14` gives `"3"` and not an escaped-then-parsed mess ([`tests/test_markupsafe.py#L19-L33`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/tests/test_markupsafe.py#L19-L33)).

## `format_field`: three doors again, in a fixed order

`vformat` finds the first field and calls `format_field(value=<User object>, format_spec='link')`. The dispatch is a familiar shape — three branches, tried in order ([`__init__.py#L339-L354`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L339-L354)):

1. `__html_format__`, if present, is called with the spec and wins outright ([L340-L341](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L340-L341)).
2. Otherwise `__html__`, if present — but only when there is no spec; a non-empty spec on an `__html__`-only object raises a `ValueError` that names the offending type ([L342-L349](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L342-L349)). Specs are never silently discarded.
3. Otherwise Python's ordinary formatting, with the spec coerced by `str(format_spec)` first so that a `Markup` spec cannot route into the wrong `__format__` callbacks ([L350-L353](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L350-L353)).

Our `User` defines `__html_format__`, so door one. The spec `'link'` is handed over as an opaque string; MarkupSafe imposes no grammar on it and makes no attempt to interpret it. `Markup` itself takes the strictest possible line on specs for its own values: `Markup.__html_format__` raises `ValueError("Unsupported format specification for Markup.")` for anything non-empty ([`__init__.py#L325-L329`](https://github.com/pallets/markupsafe/blob/b2e4d9c7687be25695fffbe93a37622302b24fb1/src/markupsafe/__init__.py#L325-L329)) — `{x:>10}` on safe markup is an error, not padding, because padding escaped text would be measuring the wrong length.

All three doors are `hasattr` checks. Any object that merely *claims* these method names is believed, which is the same duck-typed trust as `__html__`, extended to formatting.

Inside `User.__html_format__`, the spec is `"link"`, so the first thing built is another trusted literal: `Markup('<a href="/user/{}">{}</a>')` — the constructor again, again doing nothing but changing the type. Then the arguments are evaluated: the integer `3`, and `self.__html__()`, which constructs its own literal `Markup('<span class="user">{0}</span>')` and is about to format the name into it.

Two template literals now exist, both trusted, both waiting on values. The escaped comment is still sitting in the keyword arguments, untouched, two fields away from its turn.

> **Leaves as:** control inside `User.__html_format__`, holding `Markup('<a href="/user/{}">{}</a>')` with `self.id = 3` and the span template `Markup('<span class="user">{0}</span>')` built, about to render the name
