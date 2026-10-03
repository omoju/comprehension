# Chapter 6 · Dispatch and `make_response`: The Branches Not Taken, and the String That Becomes a Response

> **Enters as:** the active `<AppContext 4557234128 of scenario, GET 'http://localhost/'>`, with `preprocess_request` having just returned `None`, `request.url_rule` pointing at the `/` rule, `request.view_args == {}`, and `request.routing_exception is None`.

`rv` is `None`, so the `if` in `full_dispatch_request` opens and the context goes into [`dispatch_request(ctx)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L969-L993). This method is twelve lines long and three of them are branches. The request takes exactly one of them.

## Branch one: the exception parked in Chapter 4

```python
req = ctx.request

if req.routing_exception is not None:
    self.raise_routing_exception(req)
```

[That check](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L979-L982) is the first thing dispatch does, and it answers the question Chapter 4 left hanging. When `match_request` caught an `HTTPException` from the URL map and quietly stored it on the request instead of raising it, it deferred the decision to here — and *here* is inside `full_dispatch_request`'s `try`. A 404, a 405, a redirect for a missing trailing slash: all of them are re-raised at this line and immediately caught one frame up, where `handle_user_exception` turns them into ordinary responses. That deferral is deliberate. Routing happens during `push()`, before the error boundary exists; raising there would escape past every error handler the application registered.

[`raise_routing_exception`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L563-L589) is almost entirely a pass-through. It substitutes a friendlier `FormDataRoutingRedirect` only when *all* of debug mode is on, the exception is a `RequestRedirect`, its code is not 307 or 308, and the method is not GET/HEAD/OPTIONS. With `DEBUG=False` — the value the config picked up from the environment back in Chapter 1 — the first condition already fails and the original exception is re-raised unchanged. The debug helper never runs in production.

Our request matched cleanly, so `routing_exception` is `None` and the branch is skipped.

## Branch two: the `OPTIONS` reply that was decided at registration time

```python
rule: Rule = req.url_rule

if (
    getattr(rule, "provide_automatic_options", False)
    and req.method == "OPTIONS"
):
    return self.make_default_options_response(ctx)
```

[This branch](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L983-L990) reads a flag that was written long before the request existed. In Chapter 1, [`add_url_rule`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/sansio/app.py#L633-L651) saw that `OPTIONS` was not among the declared methods and that `PROVIDE_AUTOMATIC_OPTIONS` was `True`, so it added `OPTIONS` to the rule's method set and stamped `provide_automatic_options = True` onto the rule object. Had the request method been `OPTIONS`, [`make_default_options_response`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1056-L1066) would have asked the context's URL adapter for `allowed_methods()` and returned an empty response carrying only an `Allow` header — the view would never be called.

The method is `GET`. Skipped.

## Branch three: the view

```python
view_args: dict[str, t.Any] = req.view_args
return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
```

[One line](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L992-L993) does three things: it looks the view up by endpoint name (`'hello'`) in the dict `add_url_rule` populated, it passes it through `ensure_sync`, and it calls it with the matched URL variables as keyword arguments — here an empty dict, because `/` has no variable parts.

[`ensure_sync`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1068-L1080) asks `iscoroutinefunction(func)` and, for a plain `def`, returns the function unchanged — the trace records it handing back the identical `<function hello at 0x10f9b7ec0>` it was given. An `async def` view would instead be routed through [`async_to_sync`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1082-L1103), which imports `asgiref` and raises `RuntimeError("Install Flask with the 'async' extra in order to use async views.")` if it isn't installed. That failure is at call time, not import time: an async view in an app without the extra looks fine until someone requests it.

`hello()` runs and returns the str `'Hello, World!'`. That value — not a response, just a string — is what `dispatch_request` returns to `full_dispatch_request`, which passes it straight to `finalize_request`.

> **For the owner:** `ensure_sync` wraps each async view in its own event loop per request, so async views do not increase the number of concurrent requests a worker can handle — they only let a single request await concurrent I/O. Check whether any `async def` views exist in the codebase and whether `flask[async]` is in the dependency list, because a missing extra surfaces as a 500 on first request to that route rather than as an import error at startup.

## `finalize_request`: one entrance for every outcome

[`finalize_request(ctx, rv, from_error_handler=False)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1024-L1054) is where the normal path and the error path converge. Its first act is `response = self.make_response(rv)`; after that it will run `process_response` and send `request_finished`, both inside a `try`. That `try` only swallows failures when `from_error_handler` is `True` — a flag set by exactly one caller, [`handle_exception`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L951). On the normal path, a failing `after_request` function propagates out of `finalize_request` and is not hidden.

## `make_response`: the type contract

[`make_response(rv)`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1227-L1367) is 140 lines of docstring and about 70 lines of careful type dispatch, and it is the only place where "whatever the view returned" becomes "a `Response`". The string takes a short path through it, but the shape of the whole function is what the owner is signing off on.

It starts with `status = None` and `headers = None` and unpacks tuples first. A [3-tuple](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1291-L1293) is `(body, status, headers)`. A [2-tuple](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1294-L1299) is disambiguated by inspecting the second element: a `Headers`, `dict`, `tuple` or `list` means headers, anything else means status. Any other length [raises `TypeError`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1300-L1306) naming the three allowed forms. Our `rv` is not a tuple, so none of this runs.

Then the body is checked against `None`:

```python
if rv is None:
    raise TypeError(
        f"The view function for {request.endpoint!r} did not"
        " return a valid response. The function either returned"
        " None or ended without a return statement."
    )
```

[This](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1308-L1314) is a guarantee worth stating plainly: a view that forgets to return is never turned into an empty `200`. It raises, the exception lands in `full_dispatch_request`'s `except`, and — with no handler registered — becomes a 500. Loud, with the endpoint name in the message.

Next, the type ladder. `'Hello, World!'` is a `str`, so it takes [the first rung](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1317-L1327):

```python
rv = self.response_class(rv, status=status, headers=headers)
status = headers = None
```

The status and headers are handed to the `Response` constructor rather than applied afterwards, so the class can apply its own logic — the comment on those lines says exactly that. `Response.default_mimetype` is `"text/html"`, which is where the `Content-Type: text/html; charset=utf-8` on the final response comes from; the string is encoded UTF-8, giving 13 bytes. The trace records the result: `<Response 13 bytes [200 OK]>`.

The rungs not taken are the interesting ones. A [`dict` or `list`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1328-L1329) goes to `self.json.response(rv)` — JSON serialization is implicit for those two types and only those two. A [`BaseResponse` or any callable](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1330-L1345) is coerced via `force_type`, which for a callable means *evaluating it as a WSGI application*. Anything else [raises `TypeError`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1346-L1353) listing the permitted return types.

Finally the deferred `status` and `headers` are applied if they survived: [status](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1356-L1361) as a string or an int, and [headers](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1363-L1365) with `rv.headers.update(headers)` — note *update*, which extends rather than replaces. Both were set back to `None` by the str branch, so neither applies here.

> **For the owner:** The `callable(rv)` branch means a view that accidentally returns a function — a decorator mistake, a missing call — is executed as a WSGI application against the live `request.environ` rather than rejected. Treat any view whose return value is not obviously a str, bytes, dict, list, tuple, or `Response` as something to look at twice in review.

`make_response` returns the `Response` to `finalize_request`, which now holds a real HTTP response and has `process_response` left to run.

> **Leaves as:** `<Response 13 bytes [200 OK]>` — body `b'Hello, World!'`, `Content-Type: text/html; charset=utf-8`, no cookies and no `Vary` header yet — held by `finalize_request`, about to be passed to `process_response`.
