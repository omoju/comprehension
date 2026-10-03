# Chapter 5 · The Question Is Asked: Code For The Root

> **Enters as:** `Template(body=[Extends(template=Const(value='base.html')), Output([TemplateData('\n')]), Block('title'), Output([TemplateData('\n')]), Block('content')])`, every node carrying `environment`, handed to `Environment._generate(source=…, name='members.html', filename=None, defer_init=False)`

`_generate` is a hook, and it says so: four arguments in, one call out to the module-level `generate`, with `optimized=self.optimized` pulled off the environment ([environment.py#L681-L700](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L681-L700)). A subclass that wants different Python emitted overrides this one method; `NativeEnvironment` is the in-tree example.

`generate` checks that what it was given really is a `nodes.Template` and refuses anything else with a `TypeError` — you cannot compile a bare expression node into a module ([compiler.py#L111-L112](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L111-L112)). Then it builds `environment.code_generator_class(environment, name, filename, stream, defer_init, optimized)`, visits the tree, and returns the accumulated text ([compiler.py#L114-L122](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L114-L122)).

The `CodeGenerator` that wakes up is mostly empty counters. `stream` is a fresh `StringIO`, because none was passed. `optimized=True`, so an `Optimizer` is attached — the thing that will later be allowed to fold constant expressions ([compiler.py#L308-L319](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L308-L319)). And three fields that this particular template is about to exercise hard: `self.blocks = {}`, `self.extends_so_far = 0`, `self.has_known_extends = False` ([compiler.py#L324-L334](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L324-L334)).

`visit_Template` begins with an assertion that no frame was passed — this must be the outermost node — and then does the single most consequential thing in the whole compile:

```python
eval_ctx = EvalContext(self.environment, self.name)
```

([compiler.py#L825-L827](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L825-L827)). `EvalContext.__init__` looks at `environment.autoescape`, finds it callable, and calls it with the template name ([nodes.py#L76-L84](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/nodes.py#L76-L84)). The closure that `select_autoescape` built back in chapter 1 is finally asked its question. `'members.html'` ends in `.html`; the answer is `True`.

That answer is now a plain boolean on an object that every frame in this compile will share. It is not consulted again during rendering of this template's constant text and interpolations — it is *compiled in*. When chapter 6 reaches the `{{ user.username }}` inside the content block, the generator will literally write the characters `escape(` into the source because of what happened on this line.

> **For the owner:** Autoescaping is decided once, at compile time, from the template's *name*, and the decision is frozen into the cached module ([compiler.py#L825-L827](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L825-L827), [nodes.py#L80-L83](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/nodes.py#L80-L83)). A template named `email.txt` or `report` or loaded from a string gets `default=False` from `select_autoescape` and will interpolate user data unescaped. Check that every template rendering into HTML has an extension in your `enabled_extensions` list, or pass `autoescape=True` and stop depending on filenames.

The header comes next. `exported` from the runtime is sorted and emitted as one import line — `from jinja2.runtime import LoopContext, Macro, Markup, Namespace, TemplateNotFound, TemplateReference, TemplateRuntimeError, Undefined, escape, identity, internalcode, markup_join, missing, str_join` ([compiler.py#L829-L837](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L829-L837)). `is_async` is False, so the async half of that list stays out. `defer_init` is False, so `envenv` becomes `", environment=environment"` and the generated functions will capture the environment as a default argument instead of reaching for a module global.

Then two surveys of the tree. `node.find(nodes.Extends)` returns the `Extends` node, so `have_extends = True` ([compiler.py#L843-L845](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L843-L845)). And `node.find_all(nodes.Block)` walks the whole tree collecting blocks into `self.blocks` — the trace shows it yielding `Block('title')` and then `Block('content')`. The loop is also the uniqueness check: a second block with a name already in the dict calls `self.fail(f"block {block.name!r} defined twice", block.lineno)`, which raises `TemplateAssertionError` ([compiler.py#L847-L851](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L847-L851)). Block names are a flat namespace per template, and the collision is a compile-time error, not a last-one-wins.

No `ImportedName` nodes exist, so the import-alias loop writes nothing ([compiler.py#L853-L862](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L853-L862)). The load name goes out as `name = 'members.html'`, and then the function header: `def root(context, missing=missing, environment=environment):`, with `extra=1` so a blank line precedes it ([compiler.py#L864-L870](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L864-L870)).

Indent, then `write_commons` lays down the five lines every root and block function shares ([compiler.py#L719-L730](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L719-L730)):

```
resolve = context.resolve_or_missing
undefined = environment.undefined
concat = environment.concat
cond_expr_undefined = Undefined
if 0: yield None
```

The last line is a trick, and the docstring admits it: the dead branch forces Python to compile this function as a generator even when nothing in the body yields. The fourth line is a deliberate exception to configuration — the implicit `else` of an inline `if` always uses the stock `Undefined`, never your `StrictUndefined`.

Now the frame. `Frame(eval_ctx)` with no parent creates a root `Symbols` at level 0 ([compiler.py#L166-L198](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L166-L198)). `find_undeclared(node.body, ("self",))` comes back as `set()` — nothing in this template says `self` — so no `TemplateReference` is wired up ([compiler.py#L876-L878](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L876-L878)). `analyze_node` runs its fifty-eight nested calls over the tree and finds nothing to declare at this level, because the symbol visitor stops dead at `Block` nodes ([idtracking.py#L312-L313](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/idtracking.py#L312-L313)). `users` lives inside the content block; the root frame has never heard of it.

The frame is marked `toplevel = rootlevel = True`, and `require_output_check = have_extends and not self.has_known_extends` — True, for the moment ([compiler.py#L880-L883](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L880-L883)). `parent_template = None` is written. `enter_frame` has no loads to emit and returns silently ([compiler.py#L580-L595](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L580-L595)). `pull_dependencies(node.body)` walks the body looking for filter and test names to hoist into locals, and finds none — its visitor also stops at blocks ([compiler.py#L534-L548](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L534-L548), [compiler.py#L265-L266](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L265-L266)).

Then `blockvisit` writes `pass` and walks the five top-level nodes in order ([compiler.py#L440-L449](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L440-L449)).

The `Extends` node goes first, and `visit_Extends` is where the template's fate is sealed ([compiler.py#L994-L1034](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L994-L1034)). `frame.toplevel` is True, so it does not fail. `extends_so_far` is still 0, so the multiple-extends guard is skipped entirely. What gets written is:

```
parent_template = environment.get_template('base.html', 'members.html')
for name, parent_block in parent_template.blocks.items():
    context.blocks.setdefault(name, []).append(parent_block)
```

Three things to notice. The template name was a `Const`, so `visit(node.template, frame)` emitted a literal `'base.html'` — but the call itself is runtime code. Nothing has loaded `base.html` yet; this is an instruction to do so later. Second, `self.name` is passed as the `parent` argument, which is what will let `join_path` know who is asking. Third, the block-copy loop appends the parent's block functions *behind* whatever is already in `context.blocks` — the child's own entries are at index 0. That ordering is not incidental; it is the entire mechanism of `{{ super() }}`.

Then, because `frame.rootlevel` is True, `self.has_known_extends = True`, and `extends_so_far` becomes 1.

That flag changes the meaning of the remaining three top-level nodes. `visit_Output` is called for the first `Output([TemplateData('\n')])`, sees `frame.require_output_check`, sees `self.has_known_extends`, and returns without writing a character ([compiler.py#L1497-L1502](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1497-L1502)). Same for the second. `visit_Block` is called for `title` and `content`, sees `frame.toplevel` and `has_known_extends`, and returns too — the blocks are already registered in `self.blocks` and will be emitted as standalone functions shortly, so calling them from the root would be wrong ([compiler.py#L945-L952](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L945-L952)).

So those two stray newlines from chapter 4 — carried faithfully through the lexer, given their own `Output` nodes by the parser, walked by the symbol visitor — die here, silently, and never appear in the generated source.

> **For the owner:** Any content a child template places outside a `{% block %}` is discarded at compile time, with no warning ([compiler.py#L1499-L1502](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1499-L1502)). This is the documented behaviour of inheritance, but it means a template author who adds markup above `{% block content %}` sees it vanish with nothing to debug. Treat "my text disappeared" reports as a misplaced-block question first.

Had a second `{% extends %}` appeared, the same visitor would have emitted `raise TemplateRuntimeError("extended multiple times")` into the source and then raised `CompilerExit`, which `blockvisit` catches — the rest of the top-level body simply stops being compiled, because the compiler knows it can never run ([compiler.py#L1002-L1017](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1002-L1017), [compiler.py#L448-L449](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L448-L449)). Dynamic inheritance — an extends inside an `{% if %}` — is the case that keeps `has_known_extends` False and makes all those `if parent_template is None:` guards real. This template took the simple road.

`leave_frame(with_python_scope=True)` writes nothing, and `outdent` closes the function body ([compiler.py#L887-L888](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L887-L888)). One tail remains. Because `have_extends` is true and `has_known_extends` is true, the conditional wrapper is skipped and a single indented line is appended ([compiler.py#L890-L908](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L890-L908)):

```
yield from parent_template.root_render_func(context)
```

That is the whole of `root`. A child template's root function loads its parent, hands over its blocks, and delegates. It renders none of its own HTML.

> **Leaves as:** generated source whose root function reads — imports, `name = 'members.html'`, `def root(context, missing=missing, environment=environment):`, the five commons lines, `parent_template = None`, `pass`, `parent_template = environment.get_template('base.html', 'members.html')`, the block-copy loop, and `yield from parent_template.root_render_func(context)`; with `self.blocks = {'title': …, 'content': …}` still waiting to be written
