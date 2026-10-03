# Chapter 5 · `full_dispatch_request`: The Error Boundary and the Setup Lock

> **Enters as:** the active `<AppContext 4557234128 of scenario, GET 'http://localhost/'>` — `_push_count == 1`, `_session = <NullSession {}>`, `request.url_rule` matched to endpoint `'hello'`, `request.view_args == {}`, `request.routing_exception is None`.

`wsgi_app` hands the live context straight into [`full_dispatch_request(ctx)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L995-L1022). This is the method that owns the request's error boundary, and it does two pieces of bookkeeping before it dispatches anything.

The first is a check that costs nothing here:

```python
if not self._got_first_request and self.should_ignore_error is not None:
    import warnings
    warnings.warn(...)
```

[`should_ignore_error`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sansio/app.py#L928-L937) is a class attribute pinned to `None` and deprecated — subclasses that still override it get one `DeprecationWarning` on the first request, and the hook is scheduled for removal in Flask 3.3. This app doesn't override it, so the branch is skipped and the trace shows nothing at all for it.

The second is a single assignment, and it changes what the application is:

```python
self._got_first_request = True
```

## The lock closes

Up to this instruction, [`_check_setup_finished`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sansio/app.py#L410-L420) has been waving everything through — twice in Chapter 1, once for the static rule and once for `/`. After [line 1013](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1013), the same check raises:

```
AssertionError: The setup method 'route' can no longer be called on the
application. It has already handled its first request, any changes will not
be applied consistently.
```

Every registration method — `route`, `add_url_rule`, `before_request`, `after_request`, `errorhandler`, `teardown_request`, `register_blueprint`, `template_filter` — goes through the [`setupmethod`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sansio/scaffold.py#L42-L49) wrapper, which calls that check before doing any work. This answers the question Chapter 1 left open: the guard exists because a route added after serving began would be visible to some workers and not others, and a `before_request` hook added mid-flight would run for some requests and not others. Flask refuses the inconsistency rather than hiding it.

> **For the owner:** Any code path that registers routes, hooks, or error handlers lazily — on first use, inside a view, from a plugin loaded on demand — will raise `AssertionError` once a worker has served one request, and it will do so on only the workers that reached that path. Require that all registration happens during import or inside the app factory, before the app is handed to the server.

## One `try`, three things inside it

The rest of the method is small enough to quote whole:

```python
try:
    request_started.send(self, _async_wrapper=self.ensure_sync)
    rv = self.preprocess_request(ctx)
    if rv is None:
        rv = self.dispatch_request(ctx)
except Exception as e:
    rv = self.handle_user_exception(ctx, e)
return self.finalize_request(ctx, rv)
```

[Those eight lines](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1015-L1022) are the guarantee worth remembering: the `request_started` signal, the before-request hooks, and the view itself all sit inside the *same* `except Exception`. A subscriber that raises, a `before_request` that raises, and a view that raises are indistinguishable from here — all three go to [`handle_user_exception`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L868-L898), which looks for a registered error handler and, failing that, re-raises. And whichever way `rv` was produced — view return value, hook return value, or error handler output — it leaves through the one exit, `finalize_request`.

`request_started.send` fires first. Blinker is installed and nobody is connected, so it returns having found no receivers.

## `preprocess_request`: two passes over an empty table

[`preprocess_request(ctx)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1369-L1395) takes the request off the context and works out which scopes apply:

```python
req = ctx.request
names = (None, *reversed(req.blueprints))
```

`None` is the app scope; the rest are blueprint names. Computing `req.blueprints` sends the trace down a short chain: [`Request.blueprints`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/wrappers.py#L180-L195) asks [`Request.blueprint`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/wrappers.py#L161-L178), which asks [`Request.endpoint`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/wrappers.py#L146-L159). The endpoint is `'hello'` — the one set on the request during `match_request` in Chapter 4. It contains no `.`, so `blueprint` is `None` and `blueprints` is `[]`. `names` is therefore just `(None,)`.

Note what `endpoint` would be if routing had failed: `url_rule` would be `None`, `endpoint` would be `None`, `blueprints` would be `[]` — the scope machinery degrades to app-only rather than erroring. That is why a 404 still runs app-level before-request hooks.

Two loops follow. The first runs [URL value preprocessors](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1382-L1385), which can mutate `req.view_args` in place before the view ever sees them. The second runs [before-request functions](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1387-L1393):

```python
rv = self.ensure_sync(before_func)()

if rv is not None:
    return rv
```

A before-request hook that returns anything other than `None` becomes the response. The view is never called, and the remaining before-request hooks are never called either. That is the documented mechanism for things like "redirect anonymous users to the login page" — and it is also the reason a hook with an accidental `return` can silently take a route out of service.

Both dictionaries are `defaultdict`s and both are empty, so `name in self.url_value_preprocessors` and `name in self.before_request_funcs` are false for `None`, both loops do nothing, and `preprocess_request` falls through to `return None`.

> **For the owner:** Order is asymmetric and worth knowing before you debug one: preprocessing runs app scope first, then blueprints from outermost in; after-request and teardown run the reverse. A `before_request` registered on the app always sees the request before a blueprint's, and a non-`None` return from any of them cancels every hook after it plus the view. Require before-request hooks to end in an explicit `return None` unless they are deliberately short-circuiting.

Back in `full_dispatch_request`, `rv is None` is true, so the `if` opens the door to `dispatch_request(ctx)` — the next chapter's territory.

> **Leaves as:** `None` returned from `preprocess_request`, with the app now permanently closed to setup (`_got_first_request is True`), the request still carrying endpoint `'hello'`, `blueprints == []`, and dispatch about to begin inside the `try`.
