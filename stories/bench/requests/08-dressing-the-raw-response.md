# Chapter 8 · Dressing the Raw Response

> **Enters as:** `build_response(req=<PreparedRequest [GET]>, resp=<urllib3.response.HTTPResponse object at 0x10c23f910>)`

The last line of `HTTPAdapter.send` hands two objects to `build_response`: the PreparedRequest that has been travelling since Chapter 3, and a urllib3 response that knows its status and its headers and nothing about its body ([adapters.py#L365-L401](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L365-L401)). This function does no I/O. It is a wrapping: it takes what urllib3 parsed and arranges it into the shape the README promised.

It opens, as every public entry point in this library does, with `assert _is_prepared(req)` — a type-narrowing no-op at runtime that the trace faithfully records as `→ True` ([adapters.py#L375](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L375), [_types.py#L47-L52](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_types.py#L47-L52)).

## An empty Response first

`response = Response()` builds something deliberately blank ([models.py#L765-L810](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L765-L810)). The trace shows two calls inside it: a `CaseInsensitiveDict.__init__(data=None)` for the headers, and `cookiejar_from_dict({})` for a fresh empty `RequestsCookieJar` ([models.py#L776](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L776), [models.py#L798](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L798)).

Two of the blank values matter later. `self._content = False` is a sentinel distinct from `None`, and it is what `Response.content` checks to decide whether the body has ever been read ([models.py#L766](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L766)). And `self.elapsed = datetime.timedelta(0)` is a placeholder; the real figure is computed back in `Session.send`, from a clock that started before `adapter.send` and stops the moment this function returns — it measures time-to-headers, not time-to-body ([models.py#L806](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L806), [sessions.py#L781-L788](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L781-L788)).

## The status code, taken on faith

```python
response.status_code = getattr(resp, "status", None)
```
([adapters.py#L378-L379](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L378-L379))

Here it is `200`, which is what makes the object print as `<Response [200]>` ([models.py#L834-L835](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L834-L835)). The comment above the line is candid: *Fallback to None if there's no status_code, for whatever reason.* A transport object that never produced a status yields a perfectly constructible `Response` whose `status_code` is `None`.

Nothing in this function looks at the value. 200, 404 and 503 are dressed identically.

> **For the owner:** `build_response` does not inspect the status code, so a 4xx or 5xx produces an ordinary `Response` with no exception. Require `raise_for_status()` or an explicit status check in any code path that treats a response as success.

## Headers, case-folded once

```python
response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))
```
([adapters.py#L381-L382](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L381-L382))

The trace shows urllib3's `HTTPHeaderDict({'Server': 'BaseHTTP/0....harset=utf-8', 'Content-Length': '39'})` going in and four `__setitem__` calls coming out — `Server`, `Date`, `Content-Type`, `Content-Length` — each stored under its lowercased key with its original casing kept alongside ([structures.py#L59-L65](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/structures.py#L59-L65)). This is why the scenario's `r.headers["content-type"]` works later even though the server sent `Content-Type`, and why the trace's final lines show `__getitem__(key='content-type')` returning `'application/json; charset=utf-8'` without complaint.

## Deciding the encoding, from headers and nothing else

```python
response.encoding = get_encoding_from_headers(response.headers)
```
([adapters.py#L384-L385](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L384-L385))

`get_encoding_from_headers` reads `content-type`, hands it to `_parse_content_type_header`, and the trace records the split: `('application/json', {'charset': 'utf-8'})` ([utils.py#L569-L591](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L569-L591), [utils.py#L547-L566](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L547-L566)). The parser is lenient: it strips quotes and whitespace from each parameter and lowercases the key, so `charset="UTF-8"` and `; charset=utf-8` land in the same place. A `charset` present wins outright, and the function returns `'utf-8'` ([utils.py#L583-L584](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L583-L584)).

Three roads were not taken. With no charset, a content type containing `text` returns `ISO-8859-1` — the RFC 2616 default, and very often wrong for a modern UTF-8 page ([utils.py#L586-L587](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L586-L587)). A bare `application/json` returns `utf-8` on RFC 4627 grounds ([utils.py#L589-L591](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L589-L591)). Anything else — including a missing `content-type` entirely — falls off the end of the function and returns `None`, which is the signal that sends `Response.text` to statistical guessing in Chapter 10 ([utils.py#L576-L579](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L576-L579)).

Note what is *not* consulted: the body. A `<meta charset>` tag or an XML declaration has no influence here, because the body has not been read.

> **For the owner:** The encoding is derived from HTTP headers alone, and `text/*` without a charset silently becomes ISO-8859-1. Set `r.encoding` explicitly before reading `r.text` whenever you parse a response from a server you do not control.

## The live stream, and the URL

```python
response.raw = resp
response.reason = response.raw.reason
```
([adapters.py#L386-L387](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L386-L387))

`raw` is the same urllib3 object that came out of `conn.urlopen`, body still unread, connection still checked out of the pool. From here until someone drains it, this `Response` is holding a socket.

Then the URL is copied across from the request, decoded if it arrived as bytes ([adapters.py#L389-L392](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L389-L392)). `r.url` is therefore the *prepared* URL — percent-re-encoded, params appended — not the string the caller typed. On a redirect chain it would be the URL of this particular hop.

## Cookies, if the transport cooperates

```python
extract_cookies_to_jar(response.cookies, req, resp)
```
([adapters.py#L394-L395](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L394-L395))

The function's first act is a guard: if the urllib3 response has no truthy `_original_response`, it returns immediately and the jar stays empty ([cookies.py#L144-L145](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L144-L145)). Ours has one, so the adaptation proceeds: `MockRequest(request)` wraps the PreparedRequest in the `urllib2.Request` shape — the same wrapper Chapter 4 used on the way out ([cookies.py#L31-L50](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L31-L50)) — and `MockResponse(response._original_response.msg)` wraps the raw `http.client.HTTPMessage` so that `info()` returns it ([cookies.py#L114-L132](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L114-L132)). The trace shows `MockResponse.info` called twice: that is the standard library's `CookieJar.extract_cookies` reading the header block ([cookies.py#L150](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L150)).

The decision of *which* cookies may be stored — domain, path, secure, HttpOnly — is `http.cookiejar`'s, not Requests'. Our server sent no `Set-Cookie`, so the jar comes back `<RequestsCookieJar[]>`.

> **For the owner:** Cookie extraction is silently skipped when the response object lacks `_original_response`. Check this before accepting a custom transport adapter or a response-mocking library, because such a response will carry no cookies and will fail without an error.

## Two back-references, and out

```python
response.request = req
response.connection = self
```
([adapters.py#L397-L399](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/adapters.py#L397-L399))

`response.request` is what makes `r.request.headers` available to the caller — including, on this response, the `Authorization: Basic dXNlcjpwYXNz` that went out. `response.connection` is the adapter itself, and it is more than a convenience: it is the mechanism by which a response hook can issue a *new* request. `HTTPDigestAuth.handle_401` reaches through exactly this attribute — `r.connection.send(prep, **kwargs)` — to replay a request with a digest header after a 401 ([auth.py#L300-L316](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/auth.py#L300-L316)).

`build_response` returns `<Response [200]>`, and `HTTPAdapter.send` returns it unchanged. The object now has a status, case-insensitive headers, a declared encoding of `'utf-8'`, its URL, an empty cookie jar, and a pointer back to the request and the adapter — and a body that is still thirty-nine bytes sitting on an open socket.

> **Leaves as:** `<Response [200]>` with `headers={'Server': ..., 'Date': ..., 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': '39'}`, `encoding='utf-8'`, `url='http://127.0.0.1:54897/basic-auth/user/pass'`, `cookies=<RequestsCookieJar[]>`, `request` and `connection` attached, `_content` still `False` and `raw` still a live stream — returned from `HTTPAdapter.send` into `Session.send`
