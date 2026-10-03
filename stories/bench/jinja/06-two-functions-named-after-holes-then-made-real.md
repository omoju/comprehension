# Chapter 6 · Two Functions Named After Holes, Then Made Real

> **Enters as:** a `CodeGenerator` whose stream already holds the import line, `name = 'members.html'` and the whole of `def root(…)`, and whose `self.blocks` still holds `{'title': Block(name='title', …), 'content': Block(name='content', …)}` unwritten

The comment in the source is almost apologetic about it: *at this point we now have the blocks collected and can visit them too* ([compiler.py#L910-L916](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L910-L916)). The loop that follows runs once per entry in `self.blocks`, in the order `find_all` discovered them, and each pass produces one free-standing module-level function.

`self.func('block_' + name)` returns `'def block_title'` — `choose_async()` gives the empty string because `is_async` is False ([compiler.py#L604-L608](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L604-L608)) — and `writeline` emits `def block_title(context, missing=missing, environment=environment):` with `extra=1` for a blank line, passing the `Block` node so the line gets recorded in the debug map. Indent, then the same five commons lines the root function got ([compiler.py#L917-L918](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L917-L918), [compiler.py#L719-L730](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L719-L730)).

Then the frame, and here the code pauses to explain itself:

```python
# It's important that we do not make this frame a child of the
# toplevel template.  This would cause a variety of
# interesting issues with identifier tracking.
block_frame = Frame(eval_ctx)
block_frame.block_frame = True
```

([compiler.py#L919-L923](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L919-L923)). A parentless `Frame` gets a fresh `Symbols` at level 0 ([compiler.py#L177-L178](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L177-L178)). The block is being compiled as if it were its own small template, which is the honest model: at render time it will be called by *someone else's* root function, with a context it did not build.

`find_undeclared(block.body, ("self", "super"))` comes back `set()` for the title block — its body is one `Output([TemplateData('Members')])` and mentions neither name — so no `TemplateReference` and no `context.super(…)` are wired in ([compiler.py#L924-L930](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L924-L930)). `{{ super() }}` is not a runtime lookup that might or might not resolve; it is a parameter the compiler decides to create only when it sees the word in the block's own body.

`_block_vars = {}` is written, `enter_frame` finds nothing to load, `pull_dependencies` finds no filters or tests, and `blockvisit` writes `pass` and then the one output node ([compiler.py#L933-L936](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L933-L936)).

That output node is where the frozen autoescape answer from chapter 5 does its first real work. `visit_Output` tries to constant-fold each child; `TemplateData('Members')` has an `as_const`, the eval context says autoescape, so the constant comes back as `Markup('Members')`, gets escaped (a no-op on `Markup`), and — because template data is explicitly exempt from `finalize` — is returned as `str(const)` ([compiler.py#L1459-L1468](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1459-L1468)). The group is joined and `repr`'d into the source as a literal ([compiler.py#L1546-L1554](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1546-L1554)). The emitted line is `yield 'Members'`. No escaping will happen at render time for this text, because the escaping already happened, here, once.

`leave_frame(with_python_scope=True)` writes nothing and `outdent` closes the function ([compiler.py#L937-L938](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L937-L938)).

---

The second pass, for `content`, follows the identical shape and produces something with more in it. `find_undeclared` over `[Output('\n  <ul>\n  '), For(…), Output('\n  </ul>\n')]` again returns `set()`. But this time `analyze_node` has something to say: the symbol visitor reaches the `For` node, stops at the loop boundary, and visits only `node.iter` — the `Name('users', 'load')` ([idtracking.py#L289-L293](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/idtracking.py#L289-L293)). `Symbols.load` has never seen the name, so it defines a reference with a `VAR_LOAD_RESOLVE` instruction ([idtracking.py#L117-L119](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/idtracking.py#L117-L119)).

That is why `enter_frame` has work to do this time. It walks the frame's loads and, for the resolve instruction, writes one line ([compiler.py#L580-L595](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L580-L595)):

```
l_0_users = resolve('users')
```

`resolve` is `context.resolve_or_missing`, bound by `write_commons`. The lookup is hoisted to the top of the function and done exactly once, whatever the body does with it afterwards.

`pull_dependencies` again writes nothing, because this block uses no filters and no tests. Worth knowing what it *would* have written: for each filter or test name it finds, a `try: t_1 = environment.filters['x'] / except KeyError:` block defining a stub that raises `TemplateRuntimeError("No filter named 'x' found.")` when called ([compiler.py#L558-L578](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L558-L578)). Outside an `{% if %}`, an unknown filter is still a hard compile-time failure ([compiler.py#L1805-L1807](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1805-L1807)); inside one, the check is deferred to the moment the branch actually runs.

Then `blockvisit` walks the three statements. The leading text folds to `yield '\n  <ul>\n  '`. The `For` node is examined for whether it needs the full `LoopContext` machinery — it is not recursive, contains no scoped block, and `find_undeclared` finds no use of `loop` in its body — so `extended_loop` is False and the compiler emits an ordinary Python loop ([compiler.py#L1184-L1193](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1184-L1193), [compiler.py#L1249-L1272](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1249-L1272)):

```
for l_1_user in (undefined(name='users') if l_0_users is missing else l_0_users):
    _loop_vars = {}
```

The loop variable lives at level 1 because the loop frame is a child of the block frame. The iterable is wrapped in the undefined guard that `visit_Name` writes for any load that is not a known parameter ([compiler.py#L1642-L1652](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1642-L1652)) — a missing `users` becomes an `Undefined` object, not a `NameError`. Inside the body, `l_1_user` is a declared parameter, so references to it are written bare.

The `<li>` line is an `Output` with five children, alternating constant text and `Getattr` nodes. The constants fold as before. The `Getattr`s do not: `optimizeconst` hands them to the optimizer, `Name.as_const` raises `Impossible`, and they fall through to runtime evaluation ([compiler.py#L45-L58](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L45-L58), [compiler.py#L1526-L1531](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1526-L1531)). `_output_child_pre` sees a non-volatile, autoescaping eval context and writes the five characters `escape(` ([compiler.py#L1476-L1481](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1476-L1481)). The result:

```
yield '\n    <li><a href="'
yield escape(environment.getattr(l_1_user, 'url'))
yield '">'
yield escape(environment.getattr(l_1_user, 'username'))
yield '</a></li>\n  '
```

The ampersand that the scenario asserts about at the end is already accounted for, right here, as a literal function call compiled into a module that has not been executed yet.

---

Two final lines close the source. `blocks = {'title': block_title, 'content': block_content}` publishes the functions under their template names — this dict is how the parent will find the child's implementations. And `debug_info = '1=12&2=17&3=27&5=37&6=41'` records the mapping that `write` has been accumulating all along: template line 1 is generated line 12, template line 2 is line 17, and so on ([compiler.py#L940-L943](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L940-L943), [compiler.py#L453-L459](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L453-L459)). That string is what later turns a Python traceback into one that points at a template line ([environment.py#L1476-L1501](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1476-L1501)).

`generate` returns `generator.stream.getvalue()` ([compiler.py#L119-L122](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L119-L122)). The template is now a string of Python.

`Environment.compile` substitutes `'<template>'` for the missing filename — DictLoader had none to give — and calls `_compile`, which is the plain builtin: `compile(source, filename, "exec")` ([environment.py#L764-L768](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L764-L768), [environment.py#L702-L708](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L702-L708)). Out comes a code object.

`Template.from_code` builds a namespace seeded with just two entries — `environment` and `__file__` — and runs `exec(code, namespace)` ([environment.py#L1213-L1228](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1213-L1228)). The trace shows what the namespace holds afterwards: the fourteen imported runtime names, plus `name`, `root`, `block_title`, `block_content`, `blocks`, `debug_info`. Executing a module that consists of imports and `def` statements defines functions and nothing else. No template expression has run; `users` has not been looked at; the dicts in the scenario have not been touched.

> **For the owner:** Compiling a template produces real Python which is then `exec`'d in-process with no restrictions ([environment.py#L702-L708](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L702-L708), [environment.py#L1224-L1225](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1224-L1225)). Template source is code, so treat write access to your loader's templates as equivalent to write access to the application. If any template source can come from an untrusted author, use `SandboxedEnvironment`, and choose it before anything is compiled: the `sandboxed` flag changes what the code generator emits, for example `environment.call(context, …)` instead of `context.call(…)` ([compiler.py#L1881-L1884](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1881-L1884)), so it cannot be applied to an already-cached template.

`_from_namespace` lifts the pieces out into a `Template` object: `name` becomes `'members.html'`, `filename` becomes `'<template>'`, `blocks` is the dict just published, `root_render_func` is `root`, `_debug_info` is that `&`-joined string, and `_module` is `None` because nothing has been rendered. It then writes two entries back into the module namespace — `environment` and `__jinja_template__` — so the generated code can find its way home ([environment.py#L1244-L1270](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1244-L1270)). Back in `from_code`, `rv._uptodate` is set to the closure `DictLoader.get_source` handed over in chapter 2 ([environment.py#L1227](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1227), [loaders.py#L447-L449](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/loaders.py#L447-L449)).

`_load_template` stores the finished object under `(weakref.ref(loader), 'members.html')` and returns it ([environment.py#L976-L978](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L976-L978)). The question from chapter 2 is answered: a second `get_template('members.html')` finds this entry, and because `auto_reload` is on, consults `template.is_up_to_date`, which calls that closure and compares the source it captured against the mapping's current value ([environment.py#L962-L972](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L962-L972), [environment.py#L1485-L1490](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1485-L1490)). Edit the dict, and the next lookup recompiles.

> **For the owner:** Everything cached here is per-process and in-memory. With `bytecode_cache=None` (the default), every worker process pays the full lex–parse–generate–compile cost for every template it touches, on first use ([loaders.py#L130-L138](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/loaders.py#L130-L138)). If you set `cache_size=0` to "avoid stale templates", you also recompile on every single render; prefer leaving `auto_reload=True` in development and turning it off in production rather than disabling the cache.

> **Leaves as:** `<Template 'members.html'>` — `name='members.html'`, `filename='<template>'`, `blocks={'title': block_title, 'content': block_content}`, `root_render_func=root`, `_debug_info='1=12&2=17&3=27&5=37&6=41'`, `_module=None` — returned to the caller and stored in the environment's `LRUCache` under `(weakref.ref(DictLoader), 'members.html')`
