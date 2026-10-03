# Chapter 8 · Fetching The Parent, Then Escaping The Ampersand

> **Enters as:** `<Context {…, 'users': [{'url': '/user/1', 'username': 'ada'}, {'url': '/user/2', 'username': 'grace'}, {'url': '/user/3', 'username': 'Tom & Jerry'}]} of 'members.html'>`, handed to `root_render_func`

The context steps into the generated `root` function and the first thing that happens is not output. It is a template lookup.

Chapter 5 described the line the compiler wrote: `visit_Extends` emitted `parent_template = environment.get_template(`, then visited the extends target, then closed the call with the current template's own name as the `parent` argument ([compiler.py#L1019-L1021](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1019-L1021)). The target was a `Const`, so what actually sits in the cached module is `environment.get_template('base.html', 'members.html')`. It runs now, mid-render, with the context already built.

That timing is the fact to hold onto. Inheritance is not resolved when a template is compiled; it is resolved every time a template is rendered. The child's root function makes a live call into the environment before producing a single byte.

---

`get_template` sees `name='base.html'`, `parent='members.html'`. `name` is not already a `Template`, and `parent` is not None, so the one branch that was skipped back in chapter 2 is taken this time ([environment.py#L1010-L1015](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1010-L1015)):

```python
if parent is not None:
    name = self.join_path(name, parent)
```

`join_path` returns `'base.html'`, unchanged. The default implementation does nothing at all — it returns its first argument ([environment.py#L943-L953](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L943-L953)) — and says so in its docstring: all lookups are relative to the loader root, and subclasses that want names relative to the importing template override this hook. It is the documented place to put a naming policy, and in this environment nobody has.

From there the name travels the road chapter 2 already mapped. `_load_template` builds the cache key `(weakref.ref(self.loader), 'base.html')` and asks the `LRUCache`; the trace records `None` — `base.html` has never been loaded in this process ([environment.py#L961-L972](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L961-L972)). `make_globals(None)` produces a fresh `ChainMap({}, env.globals)`, and `BaseLoader.load` calls `DictLoader.get_source`, which finds `'base.html'` in the mapping and hands back the source, `filename=None`, and a closure that compares the captured source against the current mapping entry ([loaders.py#L444-L450](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/loaders.py#L444-L450)).

Then the whole pipeline of chapters 3 through 6 repeats, in miniature, for the parent: tokenize, parse into `[Output, Block('title'), Output, Block('content'), Output]`, generate code, `compile`, `exec`, and store the result in the same LRU cache under its own key. The trace shows it all nested under this one call, ending with `<Template 'base.html'>`. Inheritance costs one extra compile per process, not per render — the second render of `members.html` will find both templates already in the cache.

> **For the owner:** The loader is the only thing deciding which file an `{% extends %}` or `{% include %}` may reach, and the decision happens at render time, not compile time ([compiler.py#L1019-L1021](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1019-L1021)). If any template in your system can name its parent or include target from a variable, treat that name as untrusted input and check what your loader does with it: `DictLoader` is a plain key lookup ([loaders.py#L447-L450](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/loaders.py#L447-L450)), while `FileSystemLoader` and `PackageLoader` route names through `split_template_path`, which rejects `..` segments ([loaders.py#L25-L39](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/loaders.py#L25-L39)).

---

The parent template comes back, and the next three generated lines do the thing chapter 6 left unanswered ([compiler.py#L1022-L1025](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1022-L1025)):

```python
for name, parent_block in parent_template.blocks.items():
    context.blocks.setdefault(name, []).append(parent_block)
```

`context.blocks['title']` already exists — chapter 7 built it as `[block_title]`, the child's function, at index 0 ([runtime.py#L181-L184](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L181-L184)). `setdefault` finds it and *appends*. The parent's empty `block_title` lands at index 1, behind the child's. Same for `content`. Each entry is now a two-deep stack, most-derived first, ancestors behind — which is exactly what `Context.super` walks when a template calls `{{ super() }}`: it finds the current function's index in the list and reaches for the next one, returning an `Undefined` with the message *there is no parent block called …* when it runs off the end ([runtime.py#L186-L198](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L186-L198)).

With the stacks assembled, the child's root function does its last and only other act ([compiler.py#L896-L897](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L896-L897)):

```python
yield from parent_template.root_render_func(context)
```

The same `context` object — same `vars`, same merged `parent` dict holding `users`, same `eval_ctx` — is handed to the layout. From here the parent drives, and the child exists only as two functions sitting at index 0 of two lists.

---

The parent's root function has no extends of its own, so when its `visit_Block` ran during compilation the straightforward branch was taken ([compiler.py#L972-L975](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L972-L975)):

```python
yield from context.blocks['title'][0](context)
```

Index 0. Not the parent's own `block_title`, which is sitting right there in the same module — the one at the front of the stack. The layout yields `'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <title>'`, then calls into `members.html`'s `block_title`, which yields `'Members'`, then continues with `' - My Webpage</title>\n</head>\n<body>\n    <div id="content">'`.

Then `context.blocks['content'][0](context)`, and the users finally come out of the context.

The first thing `block_content` does with them is a lookup. The compiler had emitted `l_0_users = resolve('users')` when it entered the block frame, and `resolve` is `context.resolve_or_missing` ([compiler.py#L724](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L724)). That method checks `vars` first, then `parent`, and returns the `missing` sentinel if neither has the name ([runtime.py#L239-L245](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L239-L245)). `vars` is still empty; `parent` has `users`; the trace shows the same three dicts coming back.

Had the name been absent, the value would have been `missing`, and the guard the compiler wrapped around that load — `(undefined(name='users') if l_0_users is missing else l_0_users)` ([compiler.py#L1649-L1651](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1649-L1651)) — would have produced an `Undefined` instead. That object does not complain when printed; `Undefined.__str__` returns the empty string ([runtime.py#L892-L893](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L892-L893)). Iterating it yields nothing ([runtime.py#L898-L899](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L898-L899)), so a typo in `users` here would have rendered an empty, entirely valid-looking `<ul>`.

> **For the owner:** The default `undefined` class renders missing variables as empty strings and iterates as empty sequences rather than failing ([environment.py#L311](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L311), [runtime.py#L892-L899](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L892-L899)). If a missing variable in your templates should be a bug rather than a blank, pass `undefined=StrictUndefined` to the `Environment`, which turns printing, iterating and comparing an undefined into an `UndefinedError` ([runtime.py#L1059-L1062](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L1059-L1062)).

---

The loop itself is a plain Python `for` over the list. When `visit_For` ran at compile time it asked three questions — is the loop recursive, does the body mention `loop`, does it contain a scoped block ([compiler.py#L1184-L1189](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1184-L1189)) — and all three answered no, so `extended_loop` stayed False and no `LoopContext` wrapper was emitted ([compiler.py#L1249-L1272](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1249-L1272)). The bookkeeping object that would give a template `loop.index` and `loop.last` is only built when something in the body actually asks for it.

The loop target is a different kind of name from `users`. Because `RootVisitor.visit_For` visits it with `store_as_param=True` ([idtracking.py#L200-L212](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/idtracking.py#L200-L212)), `user` is a declared parameter of its frame, and `visit_Name` skips the missing-check entirely for parameters ([compiler.py#L1642-L1654](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1642-L1654)). So inside the body it is written bare, as `l_1_user`.

Each `{{ user.url }}` compiled to `environment.getattr(l_1_user, 'url')` ([compiler.py#L1750-L1752](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1750-L1752)). The trace shows six such calls — two per user — and they are the entire dynamic surface of this render. `getattr` tries a real Python attribute first, falls back to item access, and returns an `Undefined` if both fail ([environment.py#L484-L495](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L484-L495)). The users are dicts with no `url` attribute, so each lookup falls through to `obj['url']` and succeeds: `'/user/1'`, `'ada'`, `'/user/2'`, `'grace'`, `'/user/3'`, `'Tom & Jerry'`.

Nothing here filters what a template may reach. `environment.getattr` will happily return `obj.__class__` if a template asks for it; the subclass that blocks such attributes is `SandboxedEnvironment`, and because it works by changing code generation, it has to be chosen before anything is compiled.

And then the last transformation. Around every one of those six values the compiler wrote `escape(` ([compiler.py#L1476-L1481](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/compiler.py#L1476-L1481)):

```python
if frame.eval_ctx.volatile:
    self.write("(escape if context.eval_ctx.autoescape else str)(")
elif frame.eval_ctx.autoescape:
    self.write("escape(")
else:
    self.write("str(")
```

Not volatile, autoescape True — so the middle branch was taken back in chapter 6 and `escape(...)` is literally in the cached module. MarkupSafe turns `'Tom & Jerry'` into `'Tom &amp; Jerry'`. The first two users pass through unchanged because they contain nothing to escape, which is the point: the escaping is unconditional, so no one has to remember which values are dangerous.

That also settles the question chapter 7 left open. The compile-time answer governs the output. The runtime `EvalContext` on the context matters only where the compiler left a decision open — the `volatile` branch above, `Markup` joins, a macro's default autoescape. An autoescape callable that changed its mind after a template was compiled would not change a single `escape(` in the cached module.

---

The parent's root yields its closing text — `'</div>\n</body>\n</html>'` — and the generator is exhausted. `render` wraps the whole stream in `self.environment.concat(...)` ([environment.py#L1290](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1290)), which is `"".join` ([environment.py#L287](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L287)), and one string comes back.

The two stray newlines that `members.html` had at its top level are not in it. The compiler dropped them in chapter 5, the moment it knew the template had a root-level extends — exactly as planned, three chapters earlier.

> **Leaves as:** `'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <title>Members - My Webpage</title>\n</head>\n<body>\n    <div id="content">\n  <ul>\n  \n    <li><a href="/user/1">ada</a></li>\n  \n    <li><a href="/user/2">grace</a></li>\n  \n    <li><a href="/user/3">Tom &amp; Jerry</a></li>\n  \n  </ul>\n</div>\n</body>\n</html>'`
