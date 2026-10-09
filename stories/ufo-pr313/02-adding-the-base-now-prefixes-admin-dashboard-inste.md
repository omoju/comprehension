# Chapter 2 · Adding the base now prefixes "/admin-dashboard" instead of skipping it

> **Before:** `withBase("/admin-dashboard", "/admin/")` and `withBase("/admin-dashboard", "/admin")` saw the `"/admin"` prefix and returned `"/admin-dashboard"` with no base added.

> **After:** The character after `"/admin"` is `"-"`, so the code falls through to `joinURL("/admin", "/admin-dashboard")`, which returns `"/admin/admin-dashboard"`.

The same Nuxt app needs to go the other way: given the page path `"/admin-dashboard"`, it builds a link the browser can follow. That link must start with the base `/admin/`, because the app is only served there. `withBase` exists to guarantee that prefix. Before this change, it returned a link that pointed outside the app.

The path reaches `withBase` with the base `"/admin/"`. It passes the [early exits](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L291-L293), since the base is not empty and the path has no protocol. The base is trimmed to `"/admin"`, and [the `startsWith` test](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L295) passes on both sides.

This is where the versions split. In the old code, a passing prefix test was the whole decision: `withBase` [returned the input as it was](https://github.com/unjs/ufo/blob/5fb179d51384301ffb66b48e213863a27cadd1ff/src/utils.ts#L295-L297) and treated `"/admin-dashboard"` as already based. The test failed with `expected '/admin-dashboard' to be '/admin/admin-dashboard'`.

The new code [reads the character past the base](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L296), `"-"`. It only [returns early](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L298-L300) when that character is missing, `"/"` or `"?"`. With `"-"` it falls through to [`joinURL("/admin", "/admin-dashboard")`](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L302), a call the old code never made for this input. Inside, `joinURL` [drops the segment's leading slash and appends it](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L433-L434) to `withTrailingSlash("/admin")`, which is `"/admin/"`. The result is `"/admin/admin-dashboard"`. The base written as `"/admin"` takes the same path to the same result.

The two inputs that really do carry the base are unchanged. For `"/admin/dashboard"` and `"/admin/admin-dashboard"` with base `"/admin/"`, the character after `"/admin"` is `"/"`, so each is returned untouched. As a result, `withBase` is still idempotent on its own output. Feeding it `"/admin/admin-dashboard"` again does not produce a second prefix.

> **For the reviewer:** The `"#"` gap from `withoutBase` exists here too. Reading the code, `withBase("/admin#top", "/admin")` now sees `"#"`, falls through to `joinURL`, and returns `"/admin/admin#top"`. The old code returned `"/admin#top"`. This changes a correct link into a wrong one, and no test runs it. Ask the author to add `"#"` to the boundary set, or to justify leaving it out and add a test.

> **For the reviewer:** None of the `withBase` tests put a `"?"` directly after the base. The `"?"` branch of the new condition is therefore covered only by the code itself. Request a case such as `withBase("/admin?x=1", "/admin")` expecting `"/admin?x=1"`.

With this change, `withBase` adds the prefix whenever the first segment is not exactly the base, so links to a page whose name merely starts with the base now land inside the app.
