# Chapter 2 · withBase stops dropping the base on a false prefix

> **Before:** `/admin-dashboard` reaches `withBase` with base `/admin/`, is judged to already contain the base, and comes back unchanged as `/admin-dashboard` — the base silently dropped — so the test raises `AssertionError`.
> **After:** The same input reaches the same point but is now judged *not* to contain the base, falls through to `joinURL`, and comes back as `/admin/admin-dashboard`.

Two inputs enter this span expecting the base to be prepended, and two neighbours enter expecting to be left alone. They all reach the prefix branch of `withBase`; the change decides them differently.

Follow `/admin-dashboard` with base `/admin/`. `isEmptyURL("/admin/")` is false and `hasProtocol("/admin-dashboard")` is false, so the data passes the first door. `withoutTrailingSlash("/admin/")` trims the trailing slash to give `_base` = `/admin`, and `input.startsWith("/admin")` is true — the input really does begin with those six characters (trace 74–76).

On the base run, that was the whole test. [The old code returned the input the moment `startsWith` was true](https://github.com/unjs/ufo/blob/5fb179d51384301ffb66b48e213863a27cadd1ff/src/utils.ts#L295-L297), so the data came straight back as `/admin-dashboard` (trace 75). The test expected `/admin/admin-dashboard`, so it raised `AssertionError("expected '/admin-dashboard' to be '/admin/admin-dashboard'")` (trace 73).

On the head, the function reads one character past the base before trusting the match. `nextChar = input[_base.length]` is `input[6]`, which is `-`. [The guard `!nextChar || nextChar === "/" || nextChar === "?"`](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L295-L301) is false for `-`: it is defined, and it is neither `/` nor `?`. So the early return is skipped, and the data falls through to [`joinURL(_base, input)`](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L302) — `joinURL("/admin", ["/admin-dashboard"])`.

Inside `joinURL` the trace shows the work: `isNonEmptyURL("/admin-dashboard")` returns `true`, then `withTrailingSlash("/admin")` returns `/admin/`, and the segment is appended to give `/admin/admin-dashboard` (trace 77–83). The test that failed on the base now passes.

The case `/admin-dashboard` with base `/admin` (no trailing slash) runs the identical path: `withoutTrailingSlash("/admin")` leaves `_base` = `/admin`, `input[6]` is again `-`, the guard is again false, and `joinURL` again yields `/admin/admin-dashboard` (trace 96–105). Before, it too returned the bare input and raised the same `AssertionError` (trace 95).

The two neighbours confirm the guard only touches false prefixes. For `/admin/admin-dashboard` with base `/admin/`, `_base` = `/admin` and `input[6]` is `/`; the guard's `nextChar === "/"` arm fires and the input returns unchanged — `/admin/admin-dashboard` on both sides (trace 88–90). For `/admin/dashboard` with base `/admin/`, `input[6]` is again `/`, so it returns `/admin/dashboard` unchanged on both sides (trace 110–112). These were correct before and stay correct; only the boundary character distinguishes them from the two fixed cases.

> **For the reviewer:** The new behaviour is that a base counts as "already present" only when the character after it is end-of-string, `/`, or `?`. Confirm this is the intended boundary set, because `#` is deliberately excluded here and no test exercises a fragment like `/admin#x` against base `/admin`.
