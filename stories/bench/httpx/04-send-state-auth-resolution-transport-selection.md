# Chapter 4 · send(): state, auth resolution, transport selection

> **Enters as:** `<Request('GET', 'http://testserver/')>` with `stream=ByteStream(b'')`, `extensions={'timeout': {'connect': 5.0, 'read': 5.0, 'write': 5.0, 'pool': 5.0}}`, handed to `Client.send(request, stream=False, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT)`

`request()` does nothing further with the request; it forwards it straight into `send()` ([_client.py#L825](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L825)). From here the request stops being assembled and starts being dispatched, through three nested layers — auth, redirects, single request — before anything touches the application.

## The gate at the door

The first thing `send()` does is check the client's lifecycle: if `self._state == ClientState.CLOSED`, it raises `RuntimeError("Cannot send a request, as the client has been closed.")` ([_client.py#L900-L901](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L900-L901)). Our client was moved to `OPENED` by the `with` block in chapter 1, so the check passes; the next line sets `OPENED` again, unconditionally ([_client.py#L903](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L903)). That assignment is what lets a client be used without a `with` block at all — the first `send()` opens it.

Then `follow_redirects` is resolved. The argument is the `UseClientDefault` sentinel, so the client's value wins: `False` ([_client.py#L904-L908](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L904-L908)). The sentinel exists precisely so that `follow_redirects=False` passed explicitly is distinguishable from "not passed" — `None` could not carry that distinction.

> **For the owner:** The client's state transition to `CLOSED` is one-way; after `close()` or leaving the `with` block, every subsequent `send()` raises `RuntimeError` and `__enter__` refuses to reopen it ([_client.py#L900-L901](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L900-L901), [_client.py#L1275-L1283](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1275-L1283)). Check that any long-lived client in your code is created once and shared, not created per `with` block inside a request handler.

## A no-op that is not dead code

`_set_timeout(request)` runs next ([_client.py#L910](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L910)). It checks `if "timeout" not in request.extensions` and, finding the key already there from chapter 3, returns immediately ([_client.py#L584-L591](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L584-L591)). The trace records the call and an immediate `→ None`.

It matters for the other entry point. A caller who constructs `httpx.Request(...)` by hand and passes it to `send()` bypasses `build_request` entirely, and would otherwise have no timeout attached at all. This line is what makes `client.send(hand_built_request)` inherit the client's timeout policy.

## Who gets to sign the request

`_build_request_auth(request, USE_CLIENT_DEFAULT)` resolves authentication ([_client.py#L457-L473](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L457-L473)). The sentinel means "use the client's", and the client's `_auth` is `None` (chapter 1), so the function falls through to its last resort:

```
username, password = request.url.username, request.url.password
if username or password:
    return BasicAuth(username=username, password=password)
return Auth()
```

The trace shows both property reads returning `''` ([_urls.py#L150-L157](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L150-L157), [_urls.py#L159-L166](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_urls.py#L159-L166)) — `http://testserver/` has no userinfo — so the result is a bare `<httpx.Auth>` instance, the base class, whose entire flow is one unmodified yield.

That fallback branch is worth pausing on. Any URL containing `user:pass@` produces an `Authorization: Basic ...` header without the caller ever writing `auth=`, and without a warning.

> **For the owner:** Credentials embedded in a request URL are silently converted into a Basic auth header ([_client.py#L469-L471](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L469-L471)). If any URL in your system is built from user input or a configuration string, a `user:pass@` prefix becomes a credential your client sends. Validate or strip userinfo from untrusted URLs before passing them to the client, and note that the full URL is also written to the `httpx` logger at INFO.

## The auth loop, driven as a generator

`_send_handling_auth` is the outermost of the three dispatch layers ([_client.py#L930-L962](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L930-L962)). It opens `auth.sync_auth_flow(request)` and calls `next()` on it to obtain the request to actually send.

Inside `sync_auth_flow`, the first check is `if self.requires_request_body: request.read()` ([_auth.py#L71-L72](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_auth.py#L71-L72)). The base `Auth` sets that flag `False`, so nothing is read — and it would have been a no-op anyway, since the body was already buffered at construction. The flow then delegates to `auth_flow`, which yields the request untouched ([_auth.py#L74-L75](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_auth.py#L74-L75), [_auth.py#L38-L60](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_auth.py#L38-L60)). The trace shows both calls returning the same `<Request('GET', 'http://testserver/')>`.

The generator protocol is the whole design here. Each response is pushed back into the flow with `flow.send(response)`; if the scheme wants another round trip it yields a new request, and if it is finished the generator raises `StopIteration` and the response is returned ([_client.py#L947-L951](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L947-L951)). That is how `DigestAuth` turns a 401 into a second, signed request without the client knowing anything about digest.

There is a cost attached to that generality. Before the loop goes round again, the intermediate response is fully read into memory and appended to `history` ([_client.py#L953-L956](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L953-L956)). And whatever happens, `auth_flow.close()` runs in a `finally` ([_client.py#L961-L962](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L961-L962)), so a generator-based scheme holding a lock or a file handle is always finalised.

> **For the owner:** Any auth scheme that issues more than one request causes every intermediate response body to be buffered in memory and retained in `response.history` ([_client.py#L953-L956](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L953-L956)). Confirm that the endpoints you authenticate against return small bodies on their challenge responses.

This also settles a question left open in chapter 3: can a request be sent twice? Here it can. Retries through the auth loop and through redirects both reuse `request.stream` directly ([_client.py#L573-L582](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L573-L582)), and a `ByteStream` re-yields its buffered bytes on every iteration ([_content.py#L31-L39](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_content.py#L31-L39)). A generator body would raise `StreamConsumed` on the second send — which is exactly why bodies that fit in memory are read eagerly at construction ([_models.py#L422-L423](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_models.py#L422-L423)).

## The redirect loop, entered once

`_send_handling_redirects(request, follow_redirects=False, history=[])` is the middle layer ([_client.py#L964-L999](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L964-L999)). Its first act each time round is the bound check: `if len(history) > self.max_redirects: raise TooManyRedirects(...)` ([_client.py#L970-L974](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L970-L974)). With `history == []` and `max_redirects == 20`, the loop is bounded by construction — a redirect chain cannot spin forever.

Then the request event hooks run, before the transport is touched ([_client.py#L976-L977](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L976-L977)). The list is empty in this run, so the loop body is skipped and `_send_single_request(request)` is called.

## Choosing where to send it

`_send_single_request` opens with transport selection ([_client.py#L1005](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1005)). `_transport_for_url` iterates `self._mounts`, testing each `URLPattern` against the URL, and falls through to `self._transport` if nothing matches ([_client.py#L760-L769](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L760-L769)). `_mounts` is `{}` — the proxy map came back empty in chapter 1 because supplying an explicit transport set `allow_env_proxies=False`, and no `mounts=` argument was given — so the loop body never executes and the caller's `WSGITransport` is returned. That is the answer to the question left hanging in chapter 1: with no mounts, the caller's transport handles every URL, unconditionally.

Next, `start = time.perf_counter()` ([_client.py#L1006](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1006)) — `428800.362486125` in this run. The clock starts here, before the transport is called, and will be stopped when the response body is closed.

Then a guard: `if not isinstance(request.stream, SyncByteStream): raise RuntimeError("Attempted to send an async request with a sync Client instance.")` ([_client.py#L1008-L1011](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1008-L1011)). `ByteStream` implements both interfaces, so it passes. This is where a sync/async mix-up is caught — before the application is invoked, not halfway through iterating a body.

Finally the request enters `request_context(request=request)` ([_client.py#L1013-L1014](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_client.py#L1013-L1014)). That context manager catches `httpx.RequestError` raised inside the block and stamps `.request` onto it before re-raising ([_exceptions.py#L364-L377](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/httpx/_exceptions.py#L364-L377)) — so that a timeout or connection error caught by the caller can report which request produced it. What it does *not* catch is anything that is not a `RequestError`; we will see that distinction matter in the next chapter, when the application itself runs.

The trace's next entry is `WSGITransport.handle_request`.

> **Leaves as:** the same `<Request('GET', 'http://testserver/')>`, now inside `request_context`, with `transport = <WSGITransport>`, `start = 428800.362486125`, `follow_redirects = False`, `auth = <httpx.Auth>` (base class), `history = []`, client state `OPENED`
