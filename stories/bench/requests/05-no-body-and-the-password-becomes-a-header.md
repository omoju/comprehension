# Chapter 5 · No Body, and the Password Becomes a Header

> **Enters as:** `prepare_body(data={}, files=[], json=None)` on a `PreparedRequest` whose `headers` hold four validated entries and whose `body` is `None`

The `data` is an empty dict, `files` an empty list, `json` is `None`. Those are not the caller's values — the caller passed nothing at all. `Session.request` turned `data=None` into `data or {}` and `params=None` into `params or {}` ([sessions.py#L623-L634](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L623-L634)), and `Request.__init__` turned `files=None` into `[]` ([models.py#L336-L341](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L336-L341)). Three empty containers arrive where a body might have been.

## Three ways to have a body, and none of them apply

`prepare_body` starts with `body = None` and `content_type = None` and then asks three questions in a fixed order ([models.py#L576-L652](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L576-L652)).

First: `if not data and json is not None` ([models.py#L588-L599](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L588-L599)). `data` is falsy here, but `json` is `None`, so no. Worth naming the shape of that condition anyway, because it is a precedence rule with teeth: `json=` is only honoured when `data` is falsy. Pass both and the `json` is silently dropped — no warning, no error, just a form-encoded body where you expected JSON. If it had been taken, the serialisation runs with `allow_nan=False`, so a `float('nan')` anywhere in the payload becomes an `InvalidJSONError` rather than a body no server will parse.

Second: is this a stream? ([models.py#L602-L630](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L602-L630))

```python
is_iterable = isinstance(data, Iterable) or hasattr(data, "__iter__")
if is_iterable and not isinstance(data, (str, bytes, list, tuple, Mapping)):
```

A `dict` *is* iterable, but it is also a `Mapping`, so the exclusion list catches it and the branch is skipped. This is the path a file object or a generator takes, and it is worth knowing what it does even though our data avoids it: `super_len(data)` tries to determine a length; if it finds one, `Content-Length` is set, and if it does not, `Transfer-Encoding: chunked` is set instead. It also records `self._body_position = body.tell()` so the body can be rewound if a redirect forces a resend — and if `tell()` raises `OSError`, it stores a bare `object()` sentinel instead of `None`, specifically so a later rewind attempt raises `UnrewindableBodyError` rather than silently hanging the connection ([models.py#L611-L620](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L611-L620)). Streamed bodies combined with `files` raise `NotImplementedError` outright ([models.py#L622-L625](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L622-L625)).

So control falls into the `else` ([models.py#L631-L650](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L631-L650)). Third question: `if files` — `[]` is falsy, so no multipart encoding. Then `if raw_data` — `{}` is falsy, so no form encoding either, and `_encode_params` is never called on it. `body` is still `None`, `content_type` is still `None`, and the `if content_type and (...)` guard at the end adds nothing to the headers.

## The header that is deliberately absent

What remains is one call, and the trace shows it: `prepare_content_length(body=None) → None`.

```python
if body is not None:
    length = super_len(body)
    ...
elif (
    self.method not in ("GET", "HEAD")
    and self.headers.get("Content-Length") is None
):
    self.headers["Content-Length"] = "0"
```
([models.py#L654-L668](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L654-L668))

`body` is `None`, so the first branch is out. The `elif` checks the method, and `self.method` is `'GET'` — set back in Chapter 3. So no `Content-Length` is written. Had this been a POST with no body, the same code would have written `Content-Length: 0`, because a method that *may* carry a body should say it is carrying zero bytes. A GET says nothing. Remember that absence; Chapter 7 will ask the transport what it makes of a request with neither `Content-Length` nor a body.

`self.body = body` assigns `None` and `prepare_body` returns. The request still has exactly four headers.

## The tuple becomes credentials

Now `prepare_auth(auth=('user', 'pass'), url='http://127.0.0.1:54897/basic-auth/user/pass')` ([models.py#L670-L697](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L670-L697)). This is the step the previous chapters kept deferring to.

The first thing it does is a branch we skip, and it is worth a sentence because it is a trust decision: if `auth` were `None`, Requests would call `get_auth_from_url(self.url)` and use any `user:pass@` embedded in the URL as credentials ([models.py#L678-L680](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L678-L680), [utils.py#L1070-L1084](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L1070-L1084)). A URL from an untrusted source can therefore supply its own `Authorization` header. Here `auth` is truthy, so the URL is not consulted.

Then the dispatch:

```python
if isinstance(auth, tuple) and len(auth) == 2:
    # special-case basic HTTP auth
    auth_handler = HTTPBasicAuth(*auth)
else:
    auth_handler = cast("Callable[..., PreparedRequest]", auth)
```
([models.py#L682-L688](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L682-L688))

The trace shows `HTTPBasicAuth.__init__(username='user', password='pass')`, which does nothing but store the two strings ([auth.py#L96-L98](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L96-L98)). Anything that is not a 2-tuple is simply assumed callable and invoked with the prepared request — that is the extension point every third-party auth scheme uses, and it means a bad `auth=` argument surfaces as a `TypeError` from a call, not as a validation error.

`HTTPBasicAuth.__call__(r=<PreparedRequest [GET]>)` is a single line ([auth.py#L111-L113](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L111-L113)):

```python
r.headers["Authorization"] = _basic_auth_str(self.username, self.password)
```

Inside `_basic_auth_str`, the two strings are encoded — and the encoding matters:

```python
if isinstance(username, str):
    username = username.encode("latin1")

if isinstance(password, str):
    password = password.encode("latin1")

authstr = "Basic " + to_native_string(
    b64encode(b":".join((username, password))).strip()
)
```
([auth.py#L65-L75](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L65-L75))

Latin-1, not UTF-8. `b'user:pass'` base64-encodes to `b'dXNlcjpwYXNz'`, which the trace shows passing through `to_native_string(string=b'dXNlcjpwYXNz', encoding='ascii') → 'dXNlcjpwYXNz'`, and the function returns `'Basic dXNlcjpwYXNz'`. A password containing a character outside latin-1 — any emoji, most non-Latin scripts — raises `UnicodeEncodeError` from inside preparation. Non-string credentials are coerced with a `DeprecationWarning` announcing removal in 3.0 ([auth.py#L44-L62](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L44-L62)).

The trace then shows `CaseInsensitiveDict.__setitem__(key='Authorization', value='Basic dXNlcjpwYXNz')`. Note what did *not* happen: this assignment goes straight into the dict, bypassing `check_header_validity` entirely — the validation from Chapter 4 only covers the `headers=` mapping. For a base64 string that is fine; for a custom auth handler writing a header from untrusted input, it is the caller's problem.

Note also what the code did not check. There is no inspection of the scheme. This URL is `http://`, and `Basic dXNlcjpwYXNz` is a reversible encoding, not encryption — base64-decode it and you have `user:pass`. The credentials will cross the network in a form anyone on the path can read, and Requests says nothing about it.

> **For the owner:** `prepare_auth` attaches Basic credentials to `http://` URLs with no warning and no scheme check. If your service accepts a configurable base URL, validate that it is `https://` before passing `auth=`, because the library will not. The same applies to `user:pass@host` credentials embedded in a URL, which are extracted automatically whenever `auth` is not supplied.

> **For the owner:** HTTP Basic credentials are latin-1 encoded before base64. Passwords outside latin-1 raise `UnicodeEncodeError` during request preparation, not at the server. Confirm your credential source cannot produce such characters, or catch the error at your boundary.

## The handler owns the request

Two lines follow the call, and both exist because an auth handler is allowed to do more than set one header:

```python
# Update self to reflect the auth changes.
self.__dict__.update(r.__dict__)

# Recompute Content-Length
self.prepare_content_length(self.body)
```
([models.py#L691-L697](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L691-L697))

The `__dict__.update` means a handler may return a *different* `PreparedRequest` and have its entire state adopted. The recompute exists because a handler may have replaced the body. In our run neither happened — `HTTPBasicAuth` mutates in place and returns the same object — and the trace's second `prepare_content_length(body=None) → None` is a no-op for the same reason the first one was: `body` is `None` and the method is `GET`.

Then `prepare_hooks(hooks={'response': []})` ([models.py#L722-L729](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L722-L729)) walks the one event and calls `register_hook('response', [])`, which extends the existing empty list with nothing ([models.py#L257-L270](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L257-L270)). The ordering is a contract spelled out in `prepare`'s own comments: hooks come *after* auth precisely so an auth handler can register one ([models.py#L440-L451](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L440-L451)). `HTTPDigestAuth` depends on it — its `__call__` registers `handle_401` as a response hook so it can retry a challenge ([auth.py#L339-L341](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L339-L341)).

`prepare` returns. The request is complete: `GET`, a validated URL, five headers, no body, one empty hook list. The credentials are no longer a tuple in an argument list; they are a string on an object about to be handed to a transport.

> **Leaves as:** a fully prepared `PreparedRequest [GET]` — `method='GET'`, `url='http://127.0.0.1:54897/basic-auth/user/pass'`, `body=None`, no `Content-Length`, `headers={'User-Agent': 'python-requests/2.34.2', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive', 'Authorization': 'Basic dXNlcjpwYXNz'}`, `hooks={'response': []}`
