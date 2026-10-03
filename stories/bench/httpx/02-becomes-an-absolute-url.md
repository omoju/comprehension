# Chapter 2 · "/" becomes an absolute URL

> **Enters as:** `url='/'`, handed to `client.get("/", headers={"X-Custom": "value"})`, with `base_url == URL('http://testserver')` waiting on the client

The string is one character long. It names no host, no scheme, no port — it is a path and nothing else, and on its own it could not be sent anywhere. The next few frames are about giving it an origin.

`Client.get` does almost nothing with it. The method is a forwarder: it packs its arguments and calls `self.request("GET", url, ...)` ([_client.py#L1053-L1063](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1053-L1063)). `request()` is barely thicker. It checks whether per-request `cookies=` were passed, and since `cookies is None` it skips the `DeprecationWarning` that would otherwise fire ([_client.py#L804-L810](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L804-L810)) — httpx would rather you set cookies on the client, because per-request cookies have ambiguous persistence across redirects. Then it calls `build_request()` ([_client.py#L812-L825](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L812-L825)), and the first thing `build_request` does is `url = self._merge_url(url)` ([_client.py#L366](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L366)).

## Parsing it on its own terms first

`_merge_url` does not treat `'/'` as a fragment of text to be concatenated. It parses it as a URL in its own right: `URL('/')` ([_client.py#L396](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L396)), which runs the same `urlparse` pipeline the base URL went through in chapter 1.

That pipeline opens with two checks that apply to every URL the client will ever build. A URL longer than `MAX_URL_LENGTH` (65536) raises `InvalidURL("URL too long")`, and any ASCII character that is not printable — a tab, a carriage return, a newline — raises `InvalidURL` naming the character and its position ([_urlparse.py#L218-L229](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L218-L229)). That second check is the client's guard against request-line injection: you cannot smuggle a `\r\n` through a URL argument and have it reach the wire.

> **For the owner:** URL construction rejects embedded CR, LF and tab with `InvalidURL` before any transport sees the value ([_urlparse.py#L221-L229](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L221-L229)). Note that this is an `InvalidURL`, which is not a subclass of `httpx.HTTPError` ([_exceptions.py#L271-L277](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_exceptions.py#L271-L277)); make sure callers that build URLs from untrusted input catch it explicitly rather than relying on a blanket `except httpx.HTTPError`.

The regex splits `'/'` into an empty scheme, an empty authority and a path of `'/'`. Each component is then normalised. `encode_host('')` short-circuits on the empty string and returns `''` ([_urlparse.py#L348-L350](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L348-L350)). `normalize_port('', '')` returns `None` ([_urlparse.py#L405-L406](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L405-L406)). `validate_path('/', has_scheme=False, has_authority=False)` takes the relative-URL branch and checks two things: that the path does not begin with `//`, which would be read as an authority, and that it does not begin with `:`, which would be read as a scheme ([_urlparse.py#L435-L444](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L435-L444)). A single slash passes both. Note what *didn't* run: `normalize_path` is only called when there is a scheme or an authority ([_urlparse.py#L328-L329](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L328-L329)), so a bare relative path keeps its `.` and `..` segments at this stage. Finally `quote('/', safe=PATH_SAFE)` leaves the slash alone, since `/` is in the path-safe set.

What comes back is `ParseResult(scheme='', userinfo='', host='', port=None, path='/', query=None, fragment=None)` — a URL with a path and nothing else.

## The branch that decides the host

`_merge_url` now asks the question that matters: `if merge_url.is_relative_url` ([_client.py#L397](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L397)). That property is the negation of `is_absolute_url`, which is `bool(scheme and host)` ([_urls.py#L307-L325](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L307-L325)). Both are empty, so `is_absolute_url` is `False` and `is_relative_url` is `True`.

This is a fork worth naming, because it is the whole security story of `base_url`. Had the caller passed `"http://evil.example.com/path"` instead of `"/"`, `is_relative_url` would be `False`, the function would return at the last line — `return merge_url` ([_client.py#L411](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L411)) — and `base_url` would be ignored entirely. `base_url` constrains only relative arguments.

> **For the owner:** `base_url` is a convenience for relative paths, not a containment boundary. An absolute URL argument bypasses it completely ([_client.py#L396-L411](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L396-L411)). If any URL fed to this client can come from user input, validate the host yourself before the call.

Taking the relative road, the merge is two lines:

```python
merge_raw_path = self.base_url.raw_path + merge_url.raw_path.lstrip(b"/")
return self.base_url.copy_with(raw_path=merge_raw_path)
```

([_client.py#L409-L410](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L409-L410)). The base's `raw_path` is `b'/'` — the trailing slash chapter 1 guaranteed — and `b'/'.lstrip(b"/")` is `b''`, so `merge_raw_path` is `b'/'`. The construction is always *append*, never *replace*: because the base always ends in `/` and the leading slashes are stripped from the argument, `"/path"` and `"path"` produce the same result, and neither can escape upward out of the base path at this step.

## Rebuilding on the base

`copy_with(raw_path=b'/')` routes through `URL(self, raw_path=...)` ([_urls.py#L327-L340](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L327-L340)). The keyword passes the type check — `raw_path` is declared as `bytes` — and is decoded to the string `'/'` ([_urls.py#L104-L105](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L104-L105)). Because the source is a `URL` rather than a string, it becomes `ParseResult.copy_with` ([_urls.py#L118-L119](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L118-L119)), which reassembles the base's components into a defaults dict — including `authority`, computed as `'testserver'` — overlays the new `raw_path`, and re-runs `urlparse("")` with all of them as keyword arguments ([_urlparse.py#L186-L198](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L186-L198)).

Inside, `raw_path` is split back apart at the first `?`: `kwargs["path"] = '/'`, and since there was no separator, `kwargs["query"] = None` ([_urlparse.py#L251-L255](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L251-L255)). That `None` rather than `''` is deliberate: it is how httpx distinguishes a URL with no query from one ending in a bare `?`.

Then the whole validation pipeline runs again on the merged components, which is the point of rebuilding rather than string-splicing. `encode_host('testserver')` lowercases and quotes it back to `'testserver'`. `normalize_port('', 'http')` returns `None`. `validate_path('/', has_scheme=True, has_authority=True)` now takes the *absolute* branch — the path must be empty or begin with `/` ([_urlparse.py#L429-L433](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L429-L433)) — and passes. And because there is now a scheme and an authority, `normalize_path('/')` runs this time, dropping any `.` and `..` segments ([_urlparse.py#L447-L475](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L447-L475)). With a lone slash there is nothing to drop, but this is where `base_url + "../../etc"` would be collapsed rather than sent as-is.

The result is `ParseResult(scheme='http', userinfo='', host='testserver', port=None, path='/', query=None, fragment=None)`, wrapped as `URL('http://testserver/')` and returned to `build_request`.

> **For the owner:** URL normalisation is lossy by design — scheme lowercased, default ports dropped to `None`, `.`/`..` segments collapsed, IDNA hostnames encoded or rejected with `InvalidURL` ([_urlparse.py#L318-L345](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urlparse.py#L318-L345)). If any downstream system compares or signs URL strings, compare the normalised `str(request.url)`, not the string the caller supplied.

Note what the host now is: `'testserver'`, a name that resolves nowhere. Nothing in this chapter tried to resolve it, and nothing downstream will — but that is chapter 5's story.

> **Leaves as:** `URL('http://testserver/')` — scheme `'http'`, host `'testserver'`, port `None`, path `'/'`, query `None`, fragment `None`, `raw_path == b'/'` — returned from `_merge_url` into `build_request`
