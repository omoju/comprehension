# Chapter 7 · Handing Over The Data

> **Enters as:** `Template.render(users=[{'url': '/user/1', 'username': 'ada'}, {'url': '/user/2', 'username': 'grace'}, {'url': '/user/3', 'username': 'Tom & Jerry'}])`

Three dicts in a list. Up to now the story has been about a string of template source; the users have been sitting in the caller's scope, untouched, while Jinja turned `members.html` into a module. They enter now, as keyword arguments to `render`.

The first thing `render` does is not look at them. It asks `self.environment.is_async` ([environment.py#L1282-L1285](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1282-L1285)). The answer is False — `enable_async` was never passed back in chapter 1 — so the synchronous road is taken. Had it been True, `render` would have delegated to `asyncio.run(self.render_async(...))`, which is a decision worth knowing about: it means `render()` on an async environment builds and tears down an event loop per call, and cannot be called from inside a loop that is already running. The mirror-image failure lives one method down: `render_async` on a *sync* environment raises `RuntimeError("The environment was not created with async mode enabled.")` ([environment.py#L1303-L1306](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1303-L1306)).

Then the keyword arguments are collapsed: `dict(*args, **kwargs)` ([environment.py#L1287](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1287)). That one expression is why `template.render(users=…)` and `template.render({'users': …})` mean the same thing, as the docstring promises ([environment.py#L1273-L1278](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1273-L1278)). The list becomes the single value in `{'users': [...]}`, and that dict is handed to `new_context`.

`Template.new_context` adds everything the template knows about itself and forwards the lot ([environment.py#L1382-L1384](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1382-L1384)): the environment, `name='members.html'`, `self.blocks` — the dict of two functions published at the end of chapter 6 — the vars, `shared=False`, `self.globals` (the `ChainMap` from chapter 2), and `locals=None`.

---

In the module-level `new_context` helper, the `shared` flag decides the shape of the lookup table ([runtime.py#L103-L108](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L103-L108)):

```python
if shared:
    parent = vars
else:
    parent = dict(globals or (), **vars)
```

`shared` is False, so the second line runs: a brand-new plain dict is built by copying every key out of the globals `ChainMap` and then overlaying the caller's vars on top. The trace shows the result — `cycler`, `dict`, `joiner`, `lipsum`, `namespace`, `range`, and the rest of Jinja's default namespace, with `users` added. The users list itself is not copied; the same list object the caller still holds is now reachable from the context.

Two consequences fall out of that single line. The caller's variables **win** on a name collision, silently: pass `range=…` to `render` and the template's `range` is yours, not Jinja's. And because `dict(…)` flattens the `ChainMap` into a snapshot, mutating `environment.globals` after this point has no effect on this render.

`locals` is None, so the loop that would splice in internal locals is skipped ([runtime.py#L109-L116](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L109-L116)). Then `environment.context_class(…)` is called ([runtime.py#L117-L119](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L117-L119)) — a class attribute, defaulting to `Context`, and the documented hook for applications that want to change how variable lookup works ([environment.py#L289-L291](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L289-L291)).

> **For the owner:** Caller-supplied variables overwrite environment globals of the same name in the context's lookup table ([runtime.py#L108](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L108)). Do not put security-relevant helpers in `environment.globals` and assume templates will always see your version. Check that no render-time variable name collides with a global your templates depend on.

---

`Context.__init__` lays out six fields ([runtime.py#L173-L184](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L173-L184)). `parent` is the merged dict just built. `vars` starts as `{}` — empty, and reserved: it is where `{% set %}` at template top level writes, and the class docstring is explicit that modifying it is the generated code's privilege alone ([runtime.py#L152-L156](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L152-L156)). `exported_vars` is an empty set, for macros and `{% set %}` names that an importing template may pull out. `globals_keys` is `set(globals)` — remembered so that `_get_default_module` can later tell whether an importing context has brought *new* globals along and therefore needs its own module instance rather than the cached one ([environment.py#L1435-L1439](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1435-L1439)).

And then the line that matters most for what happens next:

```python
self.blocks = {k: [v] for k, v in blocks.items()}
```

Each block name maps not to a function but to a **list** containing one function ([runtime.py#L181-L184](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L181-L184)). `context.blocks['title']` is `[block_title]`, with the child's implementation at index 0. The comment above it says why: *whenever template inheritance takes place the runtime will update this mapping with the new blocks from the template.* The list is a stack waiting for ancestors to be pushed onto its back, and index 0 — the most-derived implementation — is the one that will be called. Chapter 6 left the question of how the parent ends up calling the child's functions; this one-line comprehension is half the answer.

---

The last thing the constructor builds is a second `EvalContext` ([runtime.py#L176](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/runtime.py#L176)), and with it the autoescape callable is woken for the second time in this program's life ([nodes.py#L76-L84](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/nodes.py#L76-L84)):

```python
if callable(environment.autoescape):
    self.autoescape = environment.autoescape(template_name)
else:
    self.autoescape = environment.autoescape
```

The trace records the call — `autoescape(template_name='members.html')` → `True` — and `volatile` is set False. The first time the question was asked was in `CodeGenerator.visit_Template`, during compilation, and its answer is already frozen into the `escape(...)` calls sitting in the cached module. This second answer belongs to the *running* context. Both say True, so nothing in this render will reveal which one governs. That it is possible for them to disagree at all is a property worth holding onto; chapter 8 is where it gets settled.

> **For the owner:** Make your autoescape callable a pure function of the template name. The compiled template is cached, so a callable whose answer changes over time — on a config reload, say — will not cause recompilation, and the escaping baked into the cached module will keep reflecting the answer given the first time that template was compiled ([nodes.py#L80-L83](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/nodes.py#L80-L83), [environment.py#L976-L978](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L976-L978)).

The `Context` goes back up to `render`, which has one more thing to arrange before anything executes: the whole render is wrapped in `except Exception: self.environment.handle_exception()` ([environment.py#L1289-L1292](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L1289-L1292)). Nothing is swallowed — `handle_exception` re-raises through `rewrite_traceback_stack` ([environment.py#L935-L941](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/environment.py#L935-L941)) — but the traceback the caller sees will have been rewritten using the `debug_info` string from chapter 6, so a failure inside `block_content` points at the line in `members.html` rather than at a line of generated Python.

Not one template expression has run yet. The users list is reachable, the escaping decision is on record twice, the two block functions are stacked one deep, and `root_render_func` has not been called.

> **Leaves as:** `<Context {'range': <class 'range'>, …, 'users': [{'url': '/user/1', 'username': 'ada'}, {'url': '/user/2', 'username': 'grace'}, {'url': '/user/3', 'username': 'Tom & Jerry'}]} of 'members.html'>` — `vars={}`, `exported_vars=set()`, `blocks={'title': [block_title], 'content': [block_content]}`, `eval_ctx.autoescape=True`, `eval_ctx.volatile=False`
