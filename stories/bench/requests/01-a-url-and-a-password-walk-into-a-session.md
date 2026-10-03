# Chapter 1 · A URL and a Password Walk Into a Session

> **Enters as:** `url='http://127.0.0.1:54897/basic-auth/user/pass'`, `params=None`, `auth=('user', 'pass')`

The URL arrives as a plain string and the password as the second half of a two-element tuple. Neither has been examined yet. The first function to receive them is `requests.get`, which does almost nothing of its own: it forwards the URL, slots `params` into the keyword arguments, and hands everything to `requests.api.request` with the method spelled lowercase as `"get"` ([api.py#L74-L87](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/api.py#L74-L87)).

`request` does one thing before it passes the data along, and it is the decision that frames the whole journey: it builds a brand-new `Session` inside a `with` block ([api.py#L67-L71](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/api.py#L67-L71)). The comment above it says why — closing the session avoids leaving sockets open, which can look like a `ResourceWarning` in some cases and a memory leak in others. The cost is on the other side of the ledger: this Session will live for exactly one request and then be torn down, so there is no connection to keep alive and no cookie jar that survives into the next call.

So before the URL goes anywhere, it waits while a world is built around it.

`Session.__init__` assembles that world in one pass ([sessions.py#L442-L503](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L442-L503)). Its first act is `default_headers()`, which asks `default_user_agent()` for a string — in this run, `'python-requests/2.34.2'` — and packs four entries into a `CaseInsensitiveDict` ([utils.py#L942-L962](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L942-L962)):

```
{'User-Agent': 'python-requests/2.34.2',
 'Accept-Encoding': 'gzip, deflate',
 'Accept': '*/*',
 'Connection': 'keep-alive'}
```

These four go out on every request this library makes unless the caller overrides them. The `User-Agent` names the library and its exact version to whoever is listening; the `Accept-Encoding` value is computed once at import time from urllib3's `make_headers` ([utils.py#L91-L93](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L91-L93)), which is why it reads `gzip, deflate` here and might read differently on a machine with a Brotli library installed.

> **For the owner:** Every outgoing request discloses the library name and exact version in `User-Agent` by default. Override `session.headers['User-Agent']` if your threat model treats that as fingerprinting.

Next come the settings that will decide, several chapters from now, how much the code trusts the other end of the wire. The constructor sets them as plain attributes and the trace shows no branching: `self.auth = None`, `self.proxies = {}`, `self.stream = False`, `self.verify = True`, `self.cert = None`, `self.max_redirects = DEFAULT_REDIRECT_LIMIT` (30), and `self.trust_env = True` ([sessions.py#L450-L492](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L450-L492)). Two of these are worth marking now because they are invisible later. `verify = True` is the TLS promise: it will mean "check the server's certificate against a CA bundle" when, and only when, the URL turns out to be https. And `trust_env = True` means the surrounding process environment is allowed a vote — proxy variables, CA-bundle variables, and the user's `.netrc` file are all in scope by default.

The hooks dictionary comes from `default_hooks()`, which returns `{'response': []}` — one event, no handlers ([hooks.py#L22-L26](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/hooks.py#L22-L26)). Then `cookiejar_from_dict({})` builds an empty `RequestsCookieJar`; with an empty dict there is nothing to insert, so it iterates the (empty) jar once and returns it ([cookies.py#L579-L601](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L579-L601)).

Last, the transports. The Session constructs two `HTTPAdapter` instances and mounts them under the prefixes `'https://'` and `'http://'` ([sessions.py#L500-L503](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L500-L503)). Each adapter is built with `pool_connections=10`, `pool_maxsize=10`, `max_retries=0`, `pool_block=False`, and in its constructor the retry default is turned into a concrete object: because `max_retries == DEFAULT_RETRIES`, it takes the first branch and stores `Retry(0, read=False)` ([adapters.py#L201-L221](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L201-L221)). Had the caller passed an integer, `Retry.from_int` would have built a retry policy instead. As configured, nothing is retried — not a refused connection, not a DNS failure, not a timeout. The class docstring states this as policy: by default, Requests does not retry failed connections, and callers who want granularity should construct urllib3's `Retry` themselves ([adapters.py#L168-L174](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L168-L174)).

Each mount also calls `init_poolmanager`, which creates the urllib3 `PoolManager` that will eventually hold the socket ([adapters.py#L239-L267](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L239-L267)).

> **For the owner:** Connection failures are never retried by default, and there is no automatic backoff anywhere in this path. If this code calls a flaky dependency, mount an adapter built with an explicit `urllib3.util.Retry` and decide the retry budget deliberately rather than inheriting zero.

Two prefixes are mounted and no others. A URL beginning with `mailto:` or `ftp://` has no transport at all here — a fact that will not surface until much later, when adapter lookup fails. Our URL begins with `http://`, so one of these two adapters is already waiting for it.

With the world built, `with` calls `Session.__enter__`, which simply returns the session itself ([sessions.py#L505-L506](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L505-L506)). The URL and the credential tuple are still exactly what the caller typed — unparsed, unencoded, untouched. But they are now inside a session that has already decided, on their behalf, what headers they will carry, how many redirects they may follow, whether a certificate will be checked, and how many times they may try again if the first attempt fails.

> **Leaves as:** the same `url='http://127.0.0.1:54897/basic-auth/user/pass'` and `auth=('user', 'pass')`, now held by a live `Session` whose `headers` are `{'User-Agent': 'python-requests/2.34.2', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'}`, whose `cookies` is an empty `RequestsCookieJar`, whose defaults are `verify=True`, `stream=False`, `trust_env=True`, `max_redirects=30`, `auth=None`, `proxies={}`, and whose adapters are mounted at `'https://'` and `'http://'` with `Retry(0, read=False)`
