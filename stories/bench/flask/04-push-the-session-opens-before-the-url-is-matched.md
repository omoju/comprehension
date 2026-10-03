# Chapter 4 · Push: The Session Opens Before the URL Is Matched

> **Enters as:** `<AppContext 4557234128 of scenario, GET 'http://localhost/'>` — built and bound, `_session is None`, `_cv_token is None`, `_push_count == 0`, invisible to every proxy.

`wsgi_app` calls `ctx.push()`, and the context goes from being an object someone holds a reference to into being *the* context — the one `current_app`, `g`, `request`, and `session` all resolve to.

[`push`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L416-L444) begins by counting, not by activating:

```python
self._push_count += 1

if self._cv_token is not None:
    return
```

[Those four lines](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L428-L432) are the re-entrancy guard. A context can legitimately be pushed more than once — streaming responses do it, `stream_with_context` does it, the test client does it when preserving a context — and the counter means the expensive, observable half of push (signals, opening the session, routing) happens only on the first one. Here `_push_count` goes 0 → 1 and `_cv_token` is `None`, so execution continues into the real work.

[`self._cv_token = _cv_app.set(self)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L433-L434) installs the context in the contextvar and stashes the token needed to restore the previous state later. From this instruction on, `current_app` is this app and `g` is this context's globals, for this thread only. `appcontext_pushed.send(...)` fires immediately after; with Blinker present but no subscribers connected, it costs a dictionary lookup and returns.

## The session, before the route

Because `self._request is not None`, push does two more things, and the order is the point:

```python
# Open the session at the moment that the request context is available.
# This allows a custom open_session method to use the request context.
self._get_session()

# Match the request URL after loading the session, so that the
# session is available in custom URL converters.
if self.url_adapter is not None:
    self.match_request()
```

[The comments are the contract](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L437-L444): a custom `open_session` may use `request` and `g`, because the contextvar is already set; and a custom URL converter may read `session`, because the session is already loaded. Both of those are guarantees someone writing an extension can rely on.

[`_get_session`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L381-L393) raises `RuntimeError("There is no request in this context.")` if there is no request — not the case here — then, since `_session` is `None`, asks the app's session interface to open one. The default interface is the class-level [`SecureCookieSessionInterface()`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L249-L253) shared by every `Flask` instance.

[`open_session`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L323-L335) asks for a serializer before it so much as looks at the cookies:

```python
s = self.get_signing_serializer(app)
if s is None:
    return None
```

[`get_signing_serializer`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L303-L321) reads `app.secret_key`, which is a [`ConfigAttribute`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/config.py#L35-L44) forwarding to `config["SECRET_KEY"]`. The trace records that descriptor call returning `None` — the default set in Chapter 1 and never overridden. `if not app.secret_key: return None`. No serializer, so `open_session` returns `None`, and the cookie in the request (there isn't one, but it wouldn't matter) is never read.

`_get_session` sees that `None` and falls back to [`make_null_session`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L150-L160), which constructs the interface's `null_session_class`. `SecureCookieSession.__init__` runs with `initial=None`, wiring up the `on_update` callback that would set `modified = True`, and out comes `<NullSession {}>`. That object is stored on `ctx._session` and returned.

A [`NullSession`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sessions.py#L83-L97) is a real dict-like session that is permanently empty and refuses to change: `__setitem__`, `__delitem__`, `clear`, `pop`, `popitem`, `update`, and `setdefault` are all bound to `_fail`, which raises `RuntimeError("The session is unavailable because no secret key was set. Set the secret_key on the application to something unique and secret.")`. Reads are silent — `session.get("user_id")` returns `None`, `"user_id" in session` is `False` — and only writes complain.

That is the answer to the question Chapter 1 left hanging. A missing secret key does not stop the app from starting, or from serving. It degrades the session into something that reads as empty forever and explodes the first time a view tries to write to it.

> **For the owner:** With `SECRET_KEY` unset, session reads succeed and return nothing while session writes raise `RuntimeError` at request time, which becomes a 500 for that user. A login flow would appear to work until the moment it stores anything. Set `SECRET_KEY` from the environment in every deployed configuration and fail startup if it is missing, rather than relying on this error to surface in production.

One detail worth holding onto for Chapter 7: push calls `_get_session()`, not the [`session` property](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L395-L403). Only the property sets `accessed = True`. Loading a session as part of push therefore does not, by itself, mark it accessed or earn the response a `Vary: Cookie` header.

> **For the owner:** The session is opened on every request with a request context, including requests for static files, whether or not the view touches `session`. If you replace the session interface with one backed by Redis or a database, that is a store round-trip per request. Check that any custom `open_session` is cheap, or short-circuits on paths that don't need it.

## Routing, and errors parked again

`url_adapter` is the `MapAdapter` bound in Chapter 3, so [`match_request`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L405-L414) runs:

```python
try:
    result = self.url_adapter.match(return_rule=True)
except HTTPException as e:
    self._request.routing_exception = e
else:
    self._request.url_rule, self._request.view_args = result
```

Same pattern as the adapter binding: a 404 from an unknown path, a 405 from a wrong method, a 308 `RequestRedirect` from a missing trailing slash — all of them are `HTTPException` subclasses, all of them get stored on `request.routing_exception` and none of them are raised here. Matching `/` against the two rules succeeds, so the `else` branch fires and the request now carries `url_rule` (endpoint `'hello'`) and `view_args` (`{}`). `routing_exception` stays `None`.

Parking the exception rather than raising it inside `push()` matters because of where `push()` sits: in `wsgi_app`'s inner `try`, yes, but *before* `full_dispatch_request`. An exception raised here would skip `request_started`, skip `preprocess_request`, and land in `handle_exception` rather than in the user-error path. By deferring it, Flask makes a 404 take exactly the same route through the error machinery as a 404 raised by `abort(404)` in a view. Who actually re-raises it is the next chapter's business.

`push()` returns `None`. The context is live.

> **Leaves as:** The active context — `_cv_app` set to it, `_cv_token` holding the reset token, `_push_count == 1`, `_session = <NullSession {}>` with `accessed` still `False`, `request.url_rule` the `/` rule with endpoint `'hello'`, `request.view_args == {}`, `request.routing_exception is None`.
