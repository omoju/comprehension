# Chapter 9 · Hooks, Cookie Persistence, and the Redirect That Wasn't

> **Enters as:** `<Response [200]>` with `encoding='utf-8'`, a live unread `raw`, `request` and `connection` attached — back inside `Session.send`, alongside `hooks={'response': []}` and the session's empty cookie jar

`HTTPAdapter.send` has returned. The Response is back in `Session.send`, and the first thing that happens to it is arithmetic: `elapsed = preferred_clock() - start`, converted to a `timedelta` and stored on the response ([sessions.py#L786-L788](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L786-L788)). The clock started immediately before `adapter.send` ([sessions.py#L780-L784](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L780-L784)), and it stops here — before the body is read. `r.elapsed` is time-to-headers, which is the number the docstring on the attribute promises ([models.py#L800-L806](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L800-L806)).

Then three things happen in sequence to a response that nobody has read yet: hooks get a turn at it, its cookies get copied into the session, and it gets asked whether it is a redirect.

## The hook that does nothing

```python
r = dispatch_hook("response", hooks, r, **kwargs)
```
([sessions.py#L790-L791](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L790-L791))

`hooks` is `request.hooks`, the dict prepared back in Chapter 5 ([sessions.py#L775](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L775)). The trace shows what it holds: `{'response': []}`. `dispatch_hook` looks up the key, finds an empty list, and the `if hook_list:` test is false — so it returns `hook_data` untouched ([hooks.py#L32-L48](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/hooks.py#L32-L48)). The trace confirms it: `dispatch_hook(...) → <Response [200]>`, the same object.

Two details of the road not taken are worth knowing before you sign off on a codebase that uses hooks. First, a single callable is normalised into a list, so `hooks={'response': print_url}` and `hooks={'response': [print_url]}` behave identically ([hooks.py#L42-L43](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/hooks.py#L42-L43)). Second, and more consequential: a hook's return value *replaces* the response, but only when it is not `None` ([hooks.py#L44-L47](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/hooks.py#L44-L47)). A hook that forgets to `return r` is harmless; a hook that returns something else substitutes it for everything downstream — including, as `HTTPDigestAuth.handle_401` does, a whole new response fetched over the adapter reference Chapter 8 attached ([auth.py#L300-L316](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L300-L316)).

There is no `try` around the hook call. An exception inside a hook propagates straight out of `requests.get` to the caller.

> **For the owner:** Response hooks run with the body unread and can replace the response object entirely by returning a non-`None` value. Require every hook you accept to handle its own exceptions and to return either `None` or a `Response`.

## Cookies move from the response to the session

```python
if r.history:
    for resp in r.history:
        extract_cookies_to_jar(self.cookies, resp.request, resp.raw)

extract_cookies_to_jar(self.cookies, request, r.raw)
```
([sessions.py#L793-L799](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L793-L799))

`r.history` is still the empty list `Response.__init__` gave it ([models.py#L789-L792](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L789-L792)), so the loop is skipped. The unconditional call runs, and the trace walks through it exactly as in Chapter 8: a `MockRequest` around the PreparedRequest, a `MockResponse` around `response._original_response.msg`, and two `info()` calls as the standard library's `CookieJar.extract_cookies` reads the header block ([cookies.py#L135-L150](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L135-L150)).

The difference from Chapter 8 is the destination. There the jar was `response.cookies`, a per-response record. Here it is `self.cookies` — the Session's jar, created in `Session.__init__` ([sessions.py#L494-L498](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L494-L498)). This line, and the loop above it, are the whole of Requests' cookie-persistence guarantee: cookies accumulate on the *Session*, which is why the documented pattern for a login flow is to reuse one. Our server sent no `Set-Cookie`, so the jar is unchanged and still empty.

The history loop exists for a specific reason, spelled out in its comment: *If the hooks create history then we want those cookies too* ([sessions.py#L793-L797](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L793-L797)). Digest auth's 401 retry appends the original response to `_r.history` inside the hook; without this loop, a cookie set alongside the 401 challenge would be lost.

> **For the owner:** Cookie persistence lives on the `Session`, not on the response. Because `requests.get` builds and discards a Session per call, a server cookie set by one top-level `requests.get` is not sent by the next — use `requests.Session()` when a flow depends on cookies.

## Asking whether to follow

`allow_redirects` was popped off the kwargs earlier and is `True`, the default that `Session.get` set ([sessions.py#L773](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L773), [sessions.py#L670-L671](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L670-L671)). So:

```python
gen = self.resolve_redirects(r, request, **kwargs)
history = [resp for resp in gen]
```
([sessions.py#L801-L805](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L801-L805))

`resolve_redirects` is a generator, so building the list is what actually runs it. The trace shows it entered with the full kwargs set — `stream=False, timeout=None, verify=True, cert=None, proxies=OrderedDict(), yield_requests=False` — which is precisely why Chapter 6's `Session.send` bothered to fill in every default: each redirect hop must be reproducible with the same settings ([sessions.py#L186-L197](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L186-L197)).

The generator's first act is the question:

```python
url = self.get_redirect_target(resp)
```
([sessions.py#L200-L204](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L200-L204))

`get_redirect_target` consults `resp.is_redirect` ([sessions.py#L134-L152](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L134-L152)), which is a conjunction of two conditions:

```python
return "location" in self.headers and self.status_code in REDIRECT_STATI
```
([models.py#L876-L881](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L876-L881))

The trace captures the first test resolving: `CaseInsensitiveDict.__getitem__(key='location') → None`. Our server sent `Server`, `Date`, `Content-Type` and `Content-Length`, and no `Location`. `is_redirect` returns `False`, `get_redirect_target` returns `None`, the `while url:` loop never executes, and the generator finishes without yielding ([sessions.py#L204](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L204)). `history` is `[]`, so the shuffling block that would pop the last response off and attach the rest as `r.history` is skipped ([sessions.py#L809-L815](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L809-L815)). And because `allow_redirects` is `True`, the `r._next` block that would compute a single next-hop PreparedRequest is skipped too ([sessions.py#L817-L824](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L817-L824)).

Note that `REDIRECT_STATI` is exactly `(301, 302, 303, 307, 308)` ([models.py#L93-L101](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L93-L101)). A 300 Multiple Choices with a `Location`, or a 302 without one, is not followed — it is simply returned.

## The road not taken, briefly

Our response stayed on the main road, but it is worth knowing what the detour does, because the detour is where the credentials from Chapter 5 would have been at risk.

On each hop the generator copies the request, consumes `resp.content` to free the socket, and checks `len(resp.history) >= self.max_redirects` — 30 by default — raising `TooManyRedirects` if exceeded ([sessions.py#L205-L222](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L205-L222)). For anything other than 307 or 308 it discards the body and the `Content-Length`, `Content-Type` and `Transfer-Encoding` headers ([sessions.py#L249-L258](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L249-L258)), and `rebuild_method` applies the browser-compatibility quirks: 303 and 302 become GET unless the method was HEAD, and a POST answered with 301 becomes a GET ([sessions.py#L370-L392](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L370-L392)).

Then the part that matters for the password. `rebuild_auth` deletes the `Authorization` header whenever `should_strip_auth` says so ([sessions.py#L309-L332](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L309-L332)), and `should_strip_auth` strips on any hostname change, permits the `http`→`https` upgrade on standard ports, permits a same-scheme hop between default ports, and otherwise strips on a changed port or scheme ([sessions.py#L154-L184](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L154-L184)). Immediately afterwards, if `trust_env` is on, `.netrc` may supply fresh credentials for the new host ([sessions.py#L329-L332](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L329-L332)). `rebuild_proxies` is similarly defensive: it always deletes `Proxy-Authorization` and re-derives it, and refuses to re-add it when the target scheme starts with `https`, so it is never leaked into a CONNECT tunnel ([sessions.py#L334-L368](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L334-L368)).

> **For the owner:** Credentials survive a same-host redirect and an `http`→`https` upgrade on default ports, and are stripped on a host, port, or downgrade change. If you send Basic auth over plaintext `http://` as this scenario does, the credentials are already on the wire in base64 before any redirect logic runs — require `https://` for any URL carrying auth.

The Response leaves this span exactly as it entered it: same object, same status, `history` still `[]`, `_next` still `None`, cookie jars still empty — and its body still unread on an open socket. The next line of `Session.send` is the one that changes that.

> **Leaves as:** the same `<Response [200]>`, unreplaced by hooks, with `history == []` and `_next is None`; the session jar still `<RequestsCookieJar[]>`; `_content` still `False` and `raw` still a live stream, about to meet `if not stream: r.content`
