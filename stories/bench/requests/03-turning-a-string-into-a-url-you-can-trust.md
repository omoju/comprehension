# Chapter 3 · Turning a String Into a URL You Can Trust

> **Enters as:** `PreparedRequest.prepare(method='GET', url='http://127.0.0.1:54897/basic-auth/user/pass', headers=CaseInsensitiveDict({'User-Agent': 'python-requests/2.34.2', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'}), files=[], data={}, params=OrderedDict(), auth=('user', 'pass'), cookies=<RequestsCookieJar[]>, hooks={'response': []}, json=None)`

The object receiving all this was built empty a few lines earlier: `method`, `url`, `headers`, `_cookies`, `body` and `_body_position` are all `None`, and `hooks` is a fresh `{'response': []}` ([models.py#L407-L422](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L407-L422)). `prepare` fills it in, and the order it does so is not incidental:

```python
self.prepare_method(method)
self.prepare_url(url, params)
self.prepare_headers(headers)
self.prepare_cookies(cookies)
self.prepare_body(data, files, json)
self.prepare_auth(auth, url)
```
([models.py#L440-L451](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L440-L451))

The comments beneath that block spell out the contract: `prepare_auth` must be last so that authentication schemes such as OAuth see a fully assembled request to sign, and `prepare_hooks` must come after `prepare_auth` because an auth handler is allowed to register a hook. Anyone subclassing `PreparedRequest` or calling these methods by hand inherits that ordering requirement.

This chapter covers the first two steps. The credentials sit in the argument list untouched the whole time.

## The method

`prepare_method` assigns the string, then normalises it: `to_native_string(self.method.upper())` ([models.py#L467-L471](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L467-L471)). The trace records `to_native_string(string='GET', encoding='ascii') → 'GET'` — the value was already a `str`, so the function returned it unchanged rather than decoding ([_internal_utils.py#L26-L36](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_internal_utils.py#L26-L36)). `self.method` is now `'GET'`. This is the third place the verb has been upper-cased on the way down; a lowercase verb from the caller is equivalent everywhere.

## The URL

`prepare_url` is the longest single piece of work in preparation, and almost all of it is validation ([models.py#L483-L563](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L483-L563)).

It starts by coercing: `bytes` are decoded as UTF-8, anything else goes through `str()` — which is how objects with a string representation are accepted ([models.py#L494-L497](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L494-L497)). Then leading whitespace is stripped, silently ([models.py#L499-L500](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L499-L500)). `'  http://…'` and `'http://…'` are the same request.

Next comes an escape hatch our URL walks straight past:

```python
if ":" in url and not url.lower().startswith("http"):
    self.url = url
    return
```
([models.py#L505-L507](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L505-L507))

A `mailto:` or `data:` URL is stored verbatim and no further checks are performed — no scheme check, no host check, no re-quoting. The comment explains why: RFC 3986 parsing throws on these, and the project chose passthrough over failure. The request does not then succeed; it dies later, when `Session.get_adapter` finds no mounted prefix and raises `InvalidSchema` (Chapter 6).

> **For the owner:** Any URL containing a colon that does not begin with `http` skips URL validation entirely and is stored as the caller gave it. Validate URLs that come from untrusted input before handing them to Requests, rather than relying on `prepare_url` to reject them.

Our URL does begin with `http`, so it goes to urllib3's `parse_url`, which splits it into `scheme='http'`, `auth=None`, `host='127.0.0.1'`, `port=54897`, `path='/basic-auth/user/pass'`, `query=None`, `fragment=None`. Four roads branch off here, and each one raises a `requests.exceptions` type **before any socket is opened**:

- a `LocationParseError` from `parse_url` becomes `InvalidURL` ([models.py#L510-L513](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L510-L513));
- no scheme becomes `MissingSchema`, with a message suggesting the `https://` form ([models.py#L515-L519](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L515-L519));
- no host becomes `InvalidURL` ([models.py#L521-L522](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L521-L522));
- a host starting with `*` or `.` becomes `InvalidURL('URL has an invalid label.')` ([models.py#L533-L534](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L533-L534)).

The wildcard check is the `else` of an internationalisation branch. `unicode_is_ascii('127.0.0.1')` is called and returns `True` — it simply tries `u_string.encode("ascii")` and reports whether that raised ([_internal_utils.py#L39-L51](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_internal_utils.py#L39-L51)). A non-ASCII host would instead be run through `idna.encode(host, uts46=True)`, with an `idna.IDNAError` converted to `UnicodeError` and then to `InvalidURL` ([models.py#L473-L481](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L473-L481), [models.py#L528-L532](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L528-L532)). Our ASCII host takes the wildcard check instead, and passes.

> **For the owner:** Every malformed-URL failure in this path is a subclass of `RequestException` raised during preparation, before a connection is attempted. Code that catches `requests.exceptions.RequestException` around a call therefore catches bad URLs too; code that only catches `ConnectionError` will not.

The netloc is then rebuilt by hand rather than reused from the parse: `auth` (absent) would be prefixed with `@`, the host appended, then `:54897` ([models.py#L536-L542](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L536-L542)). An empty path would become `/`, because bare domains are not valid URLs ([models.py#L544-L546](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L544-L546)); ours is already `/basic-auth/user/pass`.

Now the query string. `params` is an `OrderedDict()` — not a `str` or `bytes`, so it isn't passed through `to_native_string`, and not `None`, so it is encoded ([models.py#L548-L554](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L548-L554)). `_encode_params` checks in order: is it a string (no), does it support `read` (the trace shows `has_read(obj=OrderedDict()) → False`), does it have `__iter__` (yes) ([models.py#L150-L180](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L150-L180), [_types.py#L32-L34](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/_types.py#L32-L34)). So it flattens the mapping with `to_key_val_list`, which returns `[]`, and `urlencode([], doseq=True)` gives `''`. Values of `None` would have been dropped at the same point ([models.py#L171-L177](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L171-L177)) — that is the mechanism behind "a param set to `None` is not sent".

Because `enc_params` is empty, the block that would append it is skipped. Had the caller passed params for a URL that already had a query string, the two would be joined with `&`, params last ([models.py#L556-L560](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L556-L560)).

Finally the pieces are reassembled and re-quoted:

```python
url = requote_uri(urlunparse((scheme, netloc, path, "", query, fragment)))
self.url = url
```
([models.py#L562-L563](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/models.py#L562-L563))

`requote_uri` runs an unquote/quote cycle so that the result is consistently percent-encoded no matter how the caller wrote it: `unquote_unreserved` decodes only `%XX` sequences that map to unreserved characters, then `quote` escapes everything illegal while leaving reserved characters and `%` alone ([utils.py#L704-L723](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L704-L723), [utils.py#L680-L701](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L680-L701)). A broken escape sequence raises `InvalidURL` inside `unquote_unreserved`, and `requote_uri` catches it and quotes the whole URI instead — degrading rather than failing ([utils.py#L719-L723](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/src/requests/utils.py#L719-L723)). Our URL contains nothing to escape, so the trace shows it come back identical: `'http://127.0.0.1:54897/basic-auth/user/pass'`.

Two fields are now set. `self.headers` is still `None`, `self._cookies` is still `None`, `self.body` is still `None`, and the credentials are still just a tuple in the caller's frame. The next step takes the merged header mapping and decides whether anything in it is allowed near a socket.

> **Leaves as:** the same `PreparedRequest`, with `method='GET'` and `url='http://127.0.0.1:54897/basic-auth/user/pass'`; `headers`, `_cookies` and `body` still `None`
