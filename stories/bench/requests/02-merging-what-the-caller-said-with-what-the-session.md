# Chapter 2 · Merging What the Caller Said With What the Session Believes

> **Enters as:** `Session.request(method='get', url='http://127.0.0.1:54897/basic-auth/user/pass', auth=('user','pass'), params=None, data=None, headers=None, cookies=None, files=None, timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None, json=None)`

Fourteen of the sixteen arguments are `None`. The URL and the credential tuple are the only things the caller actually supplied, and `Session.request` now has to reconcile that near-emptiness with everything the Session already believes.

Its first move is a type check it doesn't need here: if the URL were `bytes` it would be decoded as UTF-8 ([sessions.py#L619-L620](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L619-L620)). Ours is already `str`, so it passes through untouched.

Then it builds a `Request` ([sessions.py#L622-L634](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L622-L634)). Two small coercions happen in the argument list: `data=data or {}` and `params=params or {}`. The trace shows the result — `Request.__init__(method='GET', url=..., headers=None, files=None, data={}, params={}, auth=('user', 'pass'), cookies=None, hooks=None, json=None)`. Note `or`, not `is None`: a falsy body such as `b''`, `0` or `[]` is replaced by an empty dict here, which is indistinguishable from "no body at all" by the time the body is prepared.

`Request.__init__` fills the remaining holes with empty containers — `files=None` becomes `[]`, `headers=None` becomes `{}`, `hooks=None` becomes `{}` — then calls `default_hooks()` for a fresh `{'response': []}` and copies the rest onto itself ([models.py#L336-L355](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L336-L355)). The method string, already upper-cased by the caller's frame, is stored as `'GET'`. It will be upper-cased a second time in a moment ([sessions.py#L542](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L542)) — harmless, and it means `'get'` and `'GET'` are equivalent inputs at every entry point.

Now the merge proper. `Session.prepare_request` is where request-level and session-level configuration meet ([sessions.py#L511-L555](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L511-L555)).

Cookies go first. `request.cookies or {}` gives `{}`, which is not a `CookieJar`, so `cookiejar_from_dict({})` builds an empty `RequestsCookieJar`. Then two nested `merge_cookies` calls pour the session's jar and then the request's jar into a **third, brand-new** `RequestsCookieJar` ([sessions.py#L524-L533](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L524-L533), [cookies.py#L604-L625](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L604-L625)). Both jars are empty, so the trace shows nothing but an iteration over nothing. The structure still matters: preparation never mutates `session.cookies`. Cookies only enter the session jar on the way back, after a response.

Next, the branch our credentials cause the code to skip:

```python
auth = request.auth
if self.trust_env and not auth and not self.auth:
    auth = get_netrc_auth(url)
```
([sessions.py#L535-L538](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L535-L538))

`auth` is `('user', 'pass')` and therefore truthy, so `get_netrc_auth` is never called — and indeed it does not appear in the trace. Had the caller omitted `auth`, this line would have read the user's `~/.netrc` (or `$NETRC`) and, if it found an entry for `127.0.0.1`, returned a `(login, password)` tuple that is treated exactly like one the caller passed ([utils.py#L231-L280](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L231-L280)). That path is silent: no warning, no log line. It is also higher-precedence than an `Authorization` header set via `headers=`, because auth is applied after headers during preparation.

> **For the owner:** With the default `trust_env=True`, credentials from the user's `.netrc` are attached automatically whenever no `auth` argument is given, and they override an `Authorization` header the caller set by hand. Set `session.trust_env = False` for any request whose credentials must come only from your code.

Then the four `merge_setting` calls that give the chapter its name ([sessions.py#L76-L105](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L76-L105)). The rules are short and worth knowing in order:

- If the session value is `None`, the request value wins outright. This is how `auth` resolves: `merge_setting(('user','pass'), None)` returns the tuple unchanged ([sessions.py#L84-L85](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L84-L85)).
- If the request value is `None`, the session value wins ([sessions.py#L87-L88](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L87-L88)).
- If either side is not a `Mapping`, there is no merging at all — the request value is returned as-is ([sessions.py#L91-L94](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L91-L94)). That is why scalar settings like `verify` and `cert` can never be half-inherited.
- Otherwise both sides are flattened with `to_key_val_list` and poured into `dict_class`, session first, request second — so request keys overwrite session keys ([sessions.py#L96-L97](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L96-L97)).
- Finally, any key whose merged value is `None` is **deleted** ([sessions.py#L99-L103](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L99-L103)).

For headers, the trace shows this in full: `to_key_val_list` turns the session's `CaseInsensitiveDict` into `[('User-Agent', 'python-requests/2.34.2'), ('Accept-Encoding', 'gzip, deflate'), ('Accept', '*/*'), ('Connection', 'keep-alive')]`, a new `CaseInsensitiveDict` is built from it, the request's empty list adds nothing, and the four-key scan for `None` values finds none. The merged result is the four session defaults, now in a container that belongs to this request alone. `params` merges `{}` with `{}` into an empty `OrderedDict()` — the default `dict_class` when no case-insensitive container is asked for.

> **For the owner:** Setting a header (or proxy, or param) to `None` on a single request is the supported way to suppress a session-level default for that request — it is removed from the merged mapping, not sent as the string "None". Reviewers should read a `None` in a per-request dict as a deletion, not an oversight.

Hooks take a separate path, because the naive merge would break them. `merge_hooks` sees `session_hooks.get("response") == []` and returns the request's hooks immediately — `{'response': []}` ([sessions.py#L108-L124](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L108-L124)). The docstring explains the special case: an empty response list on either side must not be allowed to wipe out the other side's handlers.

A fresh `PreparedRequest` is constructed ([models.py#L407-L422](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L407-L422)) and all of this is handed to its `prepare` method as keywords ([sessions.py#L540-L554](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L540-L554)). The URL is still the caller's raw string; the password is still a plain tuple element. Nothing has been encoded, validated or percent-quoted yet. That begins on the other side of the call.

> **Leaves as:** the arguments to `PreparedRequest.prepare`: `method='GET'`, `url='http://127.0.0.1:54897/basic-auth/user/pass'`, `files=[]`, `data={}`, `json=None`, `headers=CaseInsensitiveDict({'User-Agent': 'python-requests/2.34.2', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'})`, `params=OrderedDict()`, `auth=('user', 'pass')`, `cookies=<RequestsCookieJar[]>`, `hooks={'response': []}`
