# Chapter 4 · Inputs that already carry the base are still left alone

> **Before:** `"/base"`, `"/base/"` and `"/base/a"` with base `"/base"` or `"/base/"` came back unchanged, and `"/bar"` with base `"/foo"` became `"/foo/bar"`.

> **After:** The results are identical. The character after the base is missing or `"/"`, so the input is returned as it is. Protocol URLs and root bases still exit early.

A caller that builds links calls `withBase` on paths that often carry the base already. If the new check misread one of those, `"/base/a"` would come back as `"/base/base/a"`, a link to a page that doesn't exist. The previous chapters made `withBase` refuse `"/admin-dashboard"` as a match for `"/admin"`. This chapter follows the ten original `withBase` cases to confirm the refusal stops there.

The path through `withBase` is short. It [exits early](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L291-L293) on an empty or root base, or on an input with a protocol. Otherwise it [trims the base's trailing slash](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L294) and checks whether the input starts with it. On a match, the input is now returned only when [the next character is missing, `"/"` or `"?"`](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L296-L300).

The case most likely to break is `"/base"` with base `"/base/"`. The base trims to `"/base"`, which is the whole input, so `nextChar` is `undefined`. The `!nextChar` condition is true and `"/base"` comes back untouched, as [the old bare `startsWith`](https://github.com/unjs/ufo/blob/5fb179d51384301ffb66b48e213863a27cadd1ff/src/utils.ts#L295-L297) returned it. Without the end-of-string clause, this input would have fallen through to `joinURL` and gained a second `/base`.

The other three matches have `"/"` at that position. `"/base/"` with base `"/base"` returns `"/base/"`, and `"/base/a"` returns `"/base/a"` with either form of the base.

Inputs that don't start with the base never reach the guard. They go to [`joinURL`](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L302) exactly as before. `"/bar"` with base `"/foo"` becomes `"/foo/bar"`. Both `""` with base `"/foo"` and `"/"` with base `"/foo/"` become `"/foo"`, because [`joinURL` drops empty and root segments](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L430) before joining.

The early exits are unchanged too. `"https://test.com"` with base `"/base/"` stops at `hasProtocol`, and the root base `"/"` stops at `isEmptyURL`. Both return their input before any prefix logic runs.

This answers the earlier question. Inputs at a real boundary and absolute URLs come back exactly as they did, and only a base glued to a longer segment name now gets the prefix.

> **For the reviewer:** No `withBase` test puts a `"?"` right after the base. The `nextChar === "?"` branch in `withBase` runs only in theory. Ask for a case such as `withBase("/admin?tab=1", "/admin/")`, which the code says should return the input unchanged.

> **For the reviewer:** The end-of-string case has only one test, `"/base"` with base `"/base/"`. It is the case where a broken guard would double the base. Keep that test as the regression guard if this condition is ever rewritten.

`withBase` still trusts a path that truly starts with the base. It has only stopped trusting a path whose first segment merely begins with the same letters.
