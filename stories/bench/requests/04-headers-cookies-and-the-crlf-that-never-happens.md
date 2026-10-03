# Chapter 4 · Headers, Cookies, and the CRLF That Never Happens

> **Enters as:** `prepare_headers(headers=CaseInsensitiveDict({'User-Agent': 'python-requests/2.34.2', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'}))`, then `prepare_cookies(cookies=<RequestsCookieJar[]>)`

The four headers arrive as the merged `CaseInsensitiveDict` built back in Chapter 2. They are about to become the only text in this request that a caller can put arbitrary bytes into, so this is where Requests checks them.

The first thing `prepare_headers` does is throw away whatever `self.headers` was and start clean:

```python
self.headers = CaseInsensitiveDict()
if headers:
    for header in headers.items():
        # Raise exception on invalid header value.
        check_header_validity(header)
        name, value = header
        self.headers[to_native_string(name)] = value
```
([models.py#L565-L574](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L565-L574))

The trace shows the empty construction — `CaseInsensitiveDict.__init__(data=None)` — and then the loop walking the source mapping: `__len__ → 4`, an `__iter__` yielding the cased keys, and a `__getitem__` per key. `items()` on a `CaseInsensitiveDict` comes from `MutableMapping`, so it is driven by those two methods, which is why the trace shows them one pair at a time rather than a single bulk read ([structures.py#L64-L71](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/structures.py#L64-L71)).

## The check that runs on every header, every time

Each pair goes to `check_header_validity`, which is two calls to `_validate_header_part` — one for the name at validator index 0, one for the value at index 1. The trace shows exactly that shape four times over: `check_header_validity(header=('User-Agent', 'python-requests/2.34.2'))` containing `_validate_header_part(..., header_part='User-Agent', header_validator_index=0)` and one more ([utils.py#L1087-L1095](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L1087-L1095)).

`_validate_header_part` picks a regex pair by the type of the part — `str` or `bytes` — and raises `InvalidHeader` outright for anything else, so stringifying an int or a `UUID` is the caller's job ([utils.py#L1098-L1112](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L1098-L1112)). The regexes themselves are the whole defence:

```python
_VALID_HEADER_NAME_RE_STR = re.compile(r"^[^:\s][^:\r\n]*\Z")
_VALID_HEADER_VALUE_RE_STR = re.compile(r"^\S[^\r\n]*\Z|^\Z")
```
([_internal_utils.py#L13-L23](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_internal_utils.py#L13-L23))

A name may not begin with a colon or whitespace and may contain no colon, carriage return or line feed. A value may not begin with whitespace and may contain no CR or LF; the empty string is explicitly allowed by the `|^\Z` alternative. A mismatch raises `InvalidHeader` naming which part failed ([utils.py#L1114-L1119](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L1114-L1119)).

That is the answer to the question the last chapter left open. A header value like `"1\r\nX-Injected: yes"` cannot close the header block early and smuggle a second request past the server, because it never reaches the socket: preparation fails first, with a `RequestException` subclass, before a connection is attempted. Our four values are boring and all four pass.

> **For the owner:** `prepare_headers` is the only place in the request path that validates header names and values. Assigning to `prepared.headers[...]` after preparation — the documented prepared-request recipe does exactly this — stores the value without any CRLF check, and nothing downstream re-validates it. Treat direct mutation of a prepared request's headers as a trust boundary you own.

## Storing them

The surviving name is passed through `to_native_string`, which returns a `str` unchanged and decodes `bytes` as ASCII ([_internal_utils.py#L26-L36](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_internal_utils.py#L26-L36)); the trace confirms `'User-Agent' → 'User-Agent'` and so on for the other three. The *value* gets no such treatment — it is stored exactly as given, which is why `PreparedRequest.headers` is typed as holding `str | bytes` ([models.py#L401](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L401)).

Then `__setitem__` files it under a lowercased key while remembering the casing you used:

```python
self._store[key.lower()] = (key, value)
```
([structures.py#L59-L62](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/structures.py#L59-L62))

So `headers['content-type']` will later find a header the server spelled `Content-Type`, and the wire format keeps the original casing. The cost is stated in the class's own docstring: if two keys differ only in case, "the behavior is undefined" ([structures.py#L41-L45](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/structures.py#L41-L45)) — in practice the second write silently wins and the first disappears. A caller who passes both `{'Accept': 'a'}` and `{'ACCEPT': 'b'}` sends one header, not two.

Four `__setitem__` calls later, `self.headers` holds `User-Agent`, `Accept-Encoding`, `Accept`, `Connection`, in that order.

## The cookie jar, and the header that wasn't

`prepare_cookies` receives the merged `RequestsCookieJar[]` — empty. Because it is already a `cookielib.CookieJar`, it is adopted by reference rather than rebuilt; a plain dict would have gone through `cookiejar_from_dict` instead ([models.py#L712-L715](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L712-L715)).

Then `get_cookie_header` does the actual work, and it is mostly an act of translation ([cookies.py#L153-L161](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L153-L161)). Requests does not implement cookie matching itself; it hands the job to the standard library's `http.cookiejar`, which expects a `urllib2.Request`. `MockRequest` is the adapter: it wraps the `PreparedRequest` and exposes `get_type()`, `get_host()`, `get_full_url()` and friends by re-parsing `self._r.url` ([cookies.py#L31-L112](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L45-L78)). The trace shows its construction, with `is_prepared(request=<PreparedRequest [GET]>) → True` asserting that `url` and `method` are populated — which is why `prepare_url` had to run first.

Two details of that adapter carry weight. `is_unverifiable()` returns `True` unconditionally ([cookies.py#L80-L81](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L80-L81)), which affects how the stdlib's third-party-cookie policy treats the request. And `get_full_url()` prefers a caller-set `Host` header over the real URL host when deciding which domain the request is for ([cookies.py#L60-L78](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/cookies.py#L60-L78)) — so overriding `Host` changes which of your cookies get sent, not just what the server sees.

`jar.add_cookie_header(r)` then iterates the jar (the trace's `RequestsCookieJar.__iter__ → <generator object deepvalues>`), finds nothing, and writes nothing. `MockRequest.get_new_headers()` returns `{}`, `.get("Cookie")` returns `None`, and back in `prepare_cookies` the `if cookie_header is not None` guard is not taken ([models.py#L717-L720](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L717-L720)). No `Cookie` header is added. `self.headers` still has exactly four entries.

> **For the owner:** `prepare_cookies` is effectively single-use: cookielib will not regenerate a `Cookie` header that already exists, so a second call on the same object does nothing unless the header is deleted first — the method's docstring says so, and redirect handling depends on it by popping `Cookie` before re-preparing ([models.py#L699-L711](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L699-L711), [sessions.py#L260-L269](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/sessions.py#L260-L269)). If you modify cookies on a prepared request by hand, delete `headers['Cookie']` before re-preparing.

The request now has a method, a URL, four validated headers and a jar. The password is still a tuple in `prepare`'s argument list. Next come the body — there isn't one — and the moment those credentials become a header.

> **Leaves as:** the same `PreparedRequest`, with `headers = {'User-Agent': 'python-requests/2.34.2', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'}` (no `Cookie` key) and `_cookies` bound to the empty `RequestsCookieJar`; `body` still `None`
