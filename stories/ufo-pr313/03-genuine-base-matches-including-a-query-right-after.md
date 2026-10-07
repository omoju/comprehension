# Chapter 3 · Genuine base matches, including a query right after the base, are still removed

> **Before:** `"/api?test"` with base `"/api"` became `"/?test"`, `"/base/a"` became `"/a"`, and `"/base"` with base `"/base/"` became `"/"`.

> **After:** The results are the same. The character after the base is `"?"`, `"/"` or missing, so the guard lets each input through to the existing slice.

A stricter `withoutBase` carries its own risk. The Nuxt router strips the base from every request before it looks for a page. If the new check rejected real matches, `/admin/settings` would stop resolving, and so would `/admin?tab=users` or a bare `/admin`. This chapter follows the original fourteen `withoutBase` cases through the new guard. All of them come out as they did before.

Every one of these inputs goes through the same steps. `withoutBase` [trims the trailing slash from the base](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L322) and checks [the old `startsWith` test](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L323-L325). Only then does it reach [the new guard](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L326-L330). The guard looks at `nextChar`, the character at `input[_base.length]`, which is the first character past the base. It refuses only when that character exists and is neither `"/"` nor `"?"`.

The query case decides whether the change is safe, so it is worth following in detail. For `"/api?test"` with base `"/api"`, `nextChar` is `"?"`. The guard lets it pass. [The unchanged slice](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L331-L332) leaves `"?test"` and adds a leading slash, so the result is `"/?test"`. That is what [the old code](https://github.com/unjs/ufo/blob/5fb179d51384301ffb66b48e213863a27cadd1ff/src/utils.ts#L322-L323) returned too.

The segment cases work the same way with `"/"` as the next character. `"/base/a"` loses `"/base"` and becomes `"/a"`, whether the base is `"/base"` or `"/base/"`. `"/base/"` with base `"/base"` becomes `"/"`.

When the input is exactly the base, `nextChar` is `undefined`. The guard's first condition is falsy, so the input passes. `"/base"` with base `"/base/"` slices down to `""` and comes back as `"/"`. `"/base/a"` with base `"/base/a/"` does the same.

Some inputs never reach the guard. A root base `"/"` stops at [the `isEmptyURL` exit](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L319-L321), so `"/"`, `"/test/"`, `"/?test"` and `"https://test.com"` are returned as they are. Inputs that don't start with the base fail the `startsWith` test first. In those cases `"/"` stays `"/"`, `"/bar"` stays `"/bar"`, and `"https://test.com"` with base `"/base/"` is returned unchanged.

This answers the earlier question. A query directly after the base is still stripped correctly, and an input equal to the base still collapses to `"/"`.

> **For the reviewer:** Only one test covers the `"?"` boundary: `"/api?test"` with base `"/api"`. No test covers a base with a trailing slash before a query, such as `"/api?test"` with base `"/api/"`. Ask for that case, because a trailing slash is how Nuxt usually writes `baseURL`.

The guard narrows what `withoutBase` counts as a match without blocking any match the old tests depended on.
