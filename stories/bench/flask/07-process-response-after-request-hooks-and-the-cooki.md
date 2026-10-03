# Chapter 7 · `process_response`: After-Request Hooks and the Cookie That Isn't Written

> **Enters as:** `<Response 13 bytes [200 OK]>` — body `b'Hello, World!'`, `Content-Type: text/html; charset=utf-8`, no cookies, no `Vary` — held by `finalize_request`, together with the active `<AppContext 4557234128 of scenario, GET 'http://localhost/'>`.

`finalize_request` has its response object. Its next line opens a `try` and calls [`self.process_response(ctx, response)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1042-L1047). This is the application's last chance to touch the response before it leaves — and in an app with nothing registered, it is mostly a tour of the hooks that aren't there.

[`process_response`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1397-L1421) does three things in a fixed order: per-request callbacks, registered after-request functions, then the session.

## One: the callbacks this request asked for

```python
for func in ctx._after_request_functions:
    response = self.ensure_sync(func)(response)
```

[That list](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1410-L1411) lives on the context object itself, created empty in `AppContext.__init__` back in Chapter 3. The only way anything gets into it is [`after_this_request`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L139-L148), which fetches the active context, raises `RuntimeError` if there isn't one or if it has no request, and appends the function. It is scoped to this one request and dies with the context.

`hello()` registered nothing. The loop body never runs, and `response` is still the same object.

## Two: the hooks registered at setup, in reverse

```python
for name in chain(ctx.request.blueprints, (None,)):
    if name in self.after_request_funcs:
        for func in reversed(self.after_request_funcs[name]):
            response = self.ensure_sync(func)(response)
```

[This loop](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1413-L1416) is the mirror image of `preprocess_request` from Chapter 5. There, the scope order was `(None, *reversed(req.blueprints))` — app first, then outward-to-inward through the blueprints. Here it is `chain(ctx.request.blueprints, (None,))` — innermost blueprint first, app last — and within each scope the functions run in *reverse* registration order. The effect is a nesting discipline: whatever ran first on the way in runs last on the way out, so a hook that sets something up in `before_request` can rely on its paired `after_request` hook running after every inner one has finished.

The trace shows the context being asked for its request and the request computing `blueprints` again — `Request.blueprint` finds no dot in the endpoint `'hello'` and returns `None`, so `blueprints` is `[]`. The chain collapses to `(None,)`, and `self.after_request_funcs` has no `None` key because nothing was ever registered with `@app.after_request`. Nothing runs.

The contract in that line deserves naming: each function is called with the response and its return value *replaces* `response`. A hook that modifies headers and forgets to `return response` silently substitutes `None`, and the next hook — or the session code below — receives it. There is no check. The docstring on [`after_request`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sansio/scaffold.py#L494-L513) also notes the other half of the deal: if one of these raises, the remaining ones are skipped, which is why cleanup belongs in `teardown_request` and not here.

> **For the owner:** Require every `after_request` function to end with `return response`, and treat a hook that performs cleanup or resource release here as a defect — an exception in an earlier hook skips all later ones. Note also that these hooks run *before* the session is saved, so an `after_request` function cannot inspect or modify the session cookie.

## Three: the session that is never saved

```python
if not self.session_interface.is_null_session(ctx._get_session()):
    self.session_interface.save_session(self, ctx._get_session(), response)
```

[This](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1418-L1419) is where Chapter 4's missing secret key produces its visible consequence. `ctx._get_session()` returns the already-open `<NullSession {}>` — no re-opening, the context cached it during `push()`. [`is_null_session`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L162-L169) is a plain `isinstance` check against `null_session_class`, and the trace records it returning `True`. The `if` is false. `save_session` is not called.

So the response leaves with no `Set-Cookie` header and no `Vary` header. An application with no secret key is not an application with a broken session cookie; it is an application with no session cookie at all. Reads of `session` return empty, and writes raise `RuntimeError("The session is unavailable because no secret key was set...")` from [`NullSession._fail`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L89-L97), which is bound to `__setitem__`, `__delitem__`, `clear`, `pop`, `popitem`, `update` and `setdefault`.

Had a secret key been set, [`save_session`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L337-L385) would have run and made three decisions in order. First, [`Vary: Cookie` is added whenever `session.accessed` is true](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L349-L350) — merely reading the session makes the response cache-varying, which is the correct and easily-forgotten behaviour. Second, [an empty session that was modified gets the cookie deleted](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L353-L367), and an empty session that was never modified gets nothing. Third, [`should_set_cookie`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L233-L247) gates the write on `session.modified or (session.permanent and SESSION_REFRESH_EACH_REQUEST)` — so an unmodified non-permanent session costs no bandwidth.

The cookie attributes it would use come straight from the config defaults chosen in Chapter 1: [`SESSION_COOKIE_HTTPONLY=True`, but `SESSION_COOKIE_SECURE=False`, `SESSION_COOKIE_SAMESITE=None`, `SESSION_COOKIE_PARTITIONED=False`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L219-L226).

> **For the owner:** Set `SESSION_COOKIE_SECURE=True` and `SESSION_COOKIE_SAMESITE="Lax"` for any deployment served over HTTPS; the defaults are permissive so that plain-HTTP local development works, and they do not harden themselves in production. Confirm that `SECRET_KEY` is loaded from the environment in every deployed configuration — without it the app serves successfully but every session write raises a 500.

## Back out through `finalize_request`

`process_response` returns the same `<Response 13 bytes [200 OK]>` it was given. `finalize_request` then sends [`request_finished`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1045-L1047) with the response as a keyword argument — subscribers see the finished object, and because we are on the normal path with `from_error_handler=False`, an exception raised by a subscriber [propagates rather than being logged and swallowed](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1048-L1053).

Nothing is connected. The response is returned unchanged through `finalize_request`, through `full_dispatch_request`, and back to `wsgi_app`, which still has a context to pop.

> **Leaves as:** `<Response 13 bytes [200 OK]>`, the identical object that entered — no `Set-Cookie`, no `Vary`, body `'Hello, World!'` — returned from `finalize_request` to `full_dispatch_request` and on to `wsgi_app`.
