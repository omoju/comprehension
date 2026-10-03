# Chapter 3 · Crossing the Boundary: `wsgi_app` and the Context That Wraps Everything

> **Enters as:** The environ dict plus a `start_response` callable, arriving at `Flask.__call__`.

The dict stops being a test fixture here. Werkzeug's client calls the application object itself, and [`Flask.__call__`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1621-L1628) does exactly one thing with the two arguments: forwards them to `self.wsgi_app`. The indirection is deliberate and documented — it exists so middleware can be installed as `app.wsgi_app = MyMiddleware(app.wsgi_app)` without replacing the app object and losing every method hanging off it. The lookup is on the instance, so whatever is bound to `wsgi_app` at call time is what runs.

[`wsgi_app`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1595-L1619) is where the request's whole lifetime is framed, before any of it happens. Read the shape first, because the shape is the guarantee:

```python
ctx = self.request_context(environ)
error = None
try:
    try:
        ctx.push()
        response = self.full_dispatch_request(ctx)
    except Exception as e:
        error = e
        response = self.handle_exception(ctx, e)
    except:
        error = sys.exc_info()[1]
        raise
    return response(environ, start_response)
finally:
    ...
    ctx.pop(error)
```

Dispatch is wrapped twice: an inner `except Exception` that converts errors into a response, a bare `except` that records non-`Exception` escapes (a `KeyboardInterrupt`, a `SystemExit`) and re-raises them, and a `finally` that pops the context either way. Whatever happens between here and the end of the story, the context gets torn down. Chapter 8 collects on that promise.

> **For the owner:** Teardown is in a `finally`, so teardown callbacks and `request.close()` run even when a view raises or the process is interrupted. That is the guarantee worth leaning on; it is not a guarantee that `after_request` hooks ran, since those live inside the part that can fail.

## Building the context

[`request_context`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L1504-L1518) hands the environ to [`AppContext.from_environ`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L339-L348), which wraps it in `app.request_class(environ)` — Flask's `Request` — and attaches `request.json_module = app.json`, so a JSON body would be parsed by the same provider that will serialize responses. Then it constructs the context.

[`AppContext.__init__`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L307-L323) sets up the furniture: `self.app`, a fresh `g` from `app.app_ctx_globals_class()`, `url_adapter = None`, the request, `_session = None` (not yet loaded — that is Chapter 4), `_flashes = None`, and an empty `_after_request_functions` list. Then the one interesting line:

```python
try:
    self.url_adapter = app.create_url_adapter(self._request)
except HTTPException as e:
    if self._request is not None:
        self._request.routing_exception = e
```

[This try/except](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L325-L329) is the first of several places where an error is parked rather than raised. If binding fails — and it can, as we are about to see — the exception is stored on `request.routing_exception` and the context is constructed anyway, with `url_adapter` left `None`. A failure to bind becomes an ordinary HTTP error response later instead of a stack trace escaping into the WSGI server.

Finally [`_cv_token = None` and `_push_count = 0`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L331-L337): the context exists but is not active. Nothing can see it through `current_app`, `g`, or `request` yet.

## Who decides what host this is

[`create_url_adapter`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L530-L535) takes the request branch and starts with host validation:

```python
if (trusted_hosts := self.config["TRUSTED_HOSTS"]) is not None:
    request.trusted_hosts = trusted_hosts

request.host = get_host(request.environ, request.trusted_hosts)
```

`TRUSTED_HOSTS` is `None` in this app — one of the 29 defaults from Chapter 1 — so the first line is skipped and `get_host` is called with no allow-list. It reads `HTTP_HOST` out of the environ and returns it unchanged: `'localhost'`. Had the config been set, a mismatch would raise a `SecurityError` (a 400), which the `except HTTPException` above would catch and park on `routing_exception`, leaving `url_adapter` as `None`.

That answers the question Chapter 2 left open. Yes, Flask trusts the `Host` header the caller sent. Host validation is opt-in.

> **For the owner:** `TRUSTED_HOSTS` defaults to `None`, meaning any `Host` header is accepted and reflected in `request.host`, `request.url`, and anything built from them. If your app generates absolute URLs into emails or redirects, set `TRUSTED_HOSTS` to the hosts you actually serve, or validate the host at the proxy.

Next, [subdomains](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L539-L547). `url_map.host_matching` is `False`, so the first branch — which would blank `server_name` so the real host governs matching — is skipped. `self.subdomain_matching` is also `False`, so the `elif` runs and pins `subdomain` to `self.url_map.default_subdomain or ""`. The comment says why: Werkzeug's subdomain matching isn't wired up here, so Flask forces the current subdomain to the default rather than leaving it to be derived from the host. The practical consequence is that a request to `foo.localhost` would match app-level routes exactly as `localhost` does.

Then [`url_map.bind_to_environ(request.environ, server_name=None, subdomain="")`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L549-L551) returns the `MapAdapter` at `0x10fa1e900`, bound to this environ and holding the two rules registered in Chapter 1. (The [other path](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/app.py#L553-L561) — binding without a request, from `SERVER_NAME` and `APPLICATION_ROOT` — is what makes `url_for` work in a CLI command; it returns `None` when `SERVER_NAME` is unset, which is why building URLs outside a request fails with that particular error message.)

The adapter is assigned to `ctx.url_adapter`, `__init__` returns, and the context surfaces back through `from_environ` and `request_context` to `wsgi_app`. Its [`__repr__`](https://github.com/pallets/flask/blob/d73fa1cdcbd8b1465c151db8924ba58b1dd14e35/src/flask/ctx.py#L518-L525) shows what it is carrying: `<AppContext 4557234128 of scenario, GET 'http://localhost/'>`. Built, bound, and still invisible — the contextvar has not been touched.

> **Leaves as:** `<AppContext 4557234128 of scenario, GET 'http://localhost/'>` — a context holding the app, a fresh `g`, the `Request`, and a bound `MapAdapter`; `_session is None`, `_cv_token is None`, `_push_count == 0`; not yet pushed.
