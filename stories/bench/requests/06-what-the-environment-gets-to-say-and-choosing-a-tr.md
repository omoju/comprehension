# Chapter 6 · What the Environment Gets to Say, and Choosing a Transport

> **Enters as:** a complete `PreparedRequest [GET]` with `url='http://127.0.0.1:54897/basic-auth/user/pass'` and `Authorization: Basic dXNlcjpwYXNz`, back in `Session.request` alongside `proxies=None, stream=None, verify=None, cert=None`

`Session.prepare_request` hands the finished object back and `Session.request` names it `prep`. The next line looks like a safety check and is not one:

```python
assert _is_prepared(prep)
```
([sessions.py#L635-L643](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L635-L643))

The trace shows `is_prepared(request=<PreparedRequest [GET]>) → True`, and it would have shown `True` for any argument at all: the function returns `True` unconditionally at runtime, with the real check living only inside a `TYPE_CHECKING` block, explicitly so it cannot raise an `AssertionError` in production ([_types.py#L47-L52](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_types.py#L47-L52)). These asserts are type narrowing for pyright, not validation. An owner reading the source should not count them as a guarantee that `url` and `method` are set.

Then `proxies = proxies or {}` turns the caller's `None` into an empty dict, and the request's four unset transport settings go off to be reconciled with the world.

## The environment is a parameter

`merge_environment_settings(url='http://127.0.0.1:54897/basic-auth/user/pass', proxies={}, stream=None, verify=None, cert=None)` ([sessions.py#L831-L868](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L831-L868)) begins with a gate:

```python
if self.trust_env:
```

`trust_env` is `True` by default, set in `Session.__init__` back in Chapter 1 ([sessions.py#L490-L492](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L490-L492)). Inside that gate, two things that the caller never mentioned get a vote on how this request is sent.

The first is proxying. `get_environ_proxies(url, no_proxy=None)` ([utils.py#L873-L882](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L873-L882)) first asks `should_bypass_proxies` whether this host is exempt. That function reads `no_proxy` from the environment via a helper that prefers the lowercase name over the uppercase one ([utils.py#L817-L826](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L817-L826)) — the trace shows `get_proxy(key='no_proxy') → None`, so there was no list to match against. It matches hostnames exactly, with a port, as a dotted suffix, and — for IPv4 literals like ours — against CIDR ranges ([utils.py#L834-L859](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L834-L859)).

Then it does something worth flagging:

```python
with set_environ("no_proxy", no_proxy_arg):
    try:
        bypass = proxy_bypass(hostname)
```
([utils.py#L861-L865](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L861-L865))

The trace shows `set_environ(env_name='no_proxy', value=None)` entered and exited. `set_environ` writes to `os.environ` and restores the old value in a `finally` ([utils.py#L787-L807](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L787-L807)) — here `value is None` so it does nothing, but when a caller passes `no_proxy` in the `proxies` dict this is a process-global mutation performed so the platform's `proxy_bypass` can see it. In a threaded program, other threads see it too, briefly.

`should_bypass_proxies` returned `False`, so `getproxies()` was consulted and returned `{}` — no proxy variables in this environment. Had there been any, they would have been folded in with `setdefault`, meaning an explicit `proxies` argument wins per key but any key the caller left out can still be filled from `http_proxy`, `https_proxy` or `all_proxy` ([sessions.py#L846-L851](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L846-L851)).

The second environment vote is the one that matters most:

```python
if verify is True or verify is None:
    verify = (
        os.environ.get("REQUESTS_CA_BUNDLE")
        or os.environ.get("CURL_CA_BUNDLE")
        or verify
    )
```
([sessions.py#L853-L860](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L853-L860))

An environment variable can replace the default trust store with an arbitrary file path. Neither variable was set here, so `verify` stayed `None`.

> **For the owner:** With the default `trust_env=True`, the process environment can redirect the request through a proxy (`http_proxy`, `https_proxy`, `all_proxy`) and replace the CA bundle (`REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`), and `.netrc` can supply credentials when `auth` is omitted. Set `session.trust_env = False` for any request whose transport and trust configuration must come only from your code.

## Four merges, one settings dict

The remaining four lines each run the same `merge_setting` seen in Chapter 2 ([sessions.py#L862-L868](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L862-L868), [sessions.py#L76-L105](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L76-L105)), and the trace shows the first in full plus "×3 more":

- `proxies`: `{}` and `{}` are both Mappings, so they merge into `OrderedDict()`.
- `stream`: request value `None`, so the session's `False` is returned.
- `verify`: request value `None`, so the session's `True` is returned.
- `cert`: session value `None`, so the request's `None` is returned.

The result is exactly what the trace records: `{'cert': None, 'proxies': OrderedDict(), 'stream': False, 'verify': True}`. Note that `verify` and `stream` are not dicts, so they take the short-circuit at [sessions.py#L91-L94](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L91-L94) — a per-request `verify=False` wins outright over a session's `verify=True`, with no merging and no complaint.

`Session.request` stacks these on top of two more and calls send ([sessions.py#L645-L651](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L645-L651)):

```python
send_kwargs = {
    "timeout": timeout,
    "allow_redirects": allow_redirects,
}
send_kwargs.update(settings)
```

`timeout` is `None` — the caller never passed one, and nothing in this path supplies a default. `allow_redirects` is `True`.

## Session.send: defaults, a guard, and an adapter

`Session.send(request=<PreparedRequest [GET]>, **send_kwargs)` ([sessions.py#L752-L784](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L752-L784)) opens with three `setdefault` calls for `stream`, `verify` and `cert`, all no-ops because `merge_environment_settings` already filled them, and a fallback that is also skipped:

```python
if "proxies" not in kwargs:
    kwargs["proxies"] = resolve_proxies(request, self.proxies, self.trust_env)
```

The trace confirms it: between `Session.send` and `is_prepared` there is no `resolve_proxies` call. That fallback exists because `send` is a public entry point — someone can call `session.send(prepped)` directly with no settings at all, as the "prepared requests" documentation shows — and the kwargs must be complete before they are handed to hooks and to redirect resolution, so a redirect hop reproduces the same transport configuration.

Then the one real runtime guard in this span:

```python
if isinstance(request, Request):
    raise ValueError("You can only send PreparedRequests.")
```
([sessions.py#L765-L768](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L765-L768))

A `Request` has a `url` and a `method` but no `headers` `CaseInsensitiveDict`, no body, no `Authorization` header — sending one would fail deep inside urllib3 with something unintelligible, so it is rejected here by name.

`allow_redirects` is popped off into a local (`True`), `stream` is read (`False`), `hooks` is taken from the request itself, and then the question of which transport:

```python
adapter = self.get_adapter(url=request.url)
```

`get_adapter` is a linear scan over the mounted prefixes, lowercased, using `startswith` ([sessions.py#L870-L881](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L870-L881)). `Session.mount` keeps longer prefixes first by moving every shorter key to the end as each one is registered ([sessions.py#L888-L897](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L888-L897)), so a specific mount beats a general one. Our URL starts with `http://`, and the trace returns the adapter at `0x10da78190` — the second `HTTPAdapter` built in Chapter 1, the one mounted at `'http://'` on trace line 34.

The scan is a plain prefix test, not a URL-aware one. Mounting an adapter at `http://localhost` also matches `http://localhost.other.com` and `http://localhost@other.com`; the documentation says to terminate hostnames with a `/`. And when nothing matches, this is where the `mailto:` and `data:` URLs that `prepare_url` waved through in Chapter 3 finally stop: `InvalidSchema(f"No connection adapters were found for {url!r}")`.

> **For the owner:** `get_adapter` matches by string prefix, so a custom adapter mounted at `http://internal-api` will also be used for `http://internal-api.attacker.example/`. Terminate every mount prefix with a `/` when the adapter carries different credentials, certificates or retry behaviour.

One line before the send itself, a clock starts:

```python
start = preferred_clock()
```
([sessions.py#L780-L788](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L780-L788))

It stops the moment `adapter.send` returns, which is when the response *headers* have been parsed — not when the body has been read. `Response.elapsed` therefore measures time-to-headers, and is unaffected by how long the content takes or whether `stream=True` defers it.

The request, the five headers, the base64 credentials and a settings dict containing `timeout=None` now cross into the adapter, where a socket will finally open.

> **Leaves as:** `adapter = <HTTPAdapter at 0x10da78190>` (mounted at `'http://'`) about to receive `request=<PreparedRequest [GET]>, stream=False, timeout=None, verify=True, cert=None, proxies=OrderedDict()`
