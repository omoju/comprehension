# Chapter 1 · Removing the base no longer cuts "/admin" out of "/admin-dashboard"

> **Before:** `withoutBase("/admin-dashboard", "/admin/")` and `withoutBase("/admin-dashboard", "/admin")` matched `"/admin"` as a prefix and returned `"/-dashboard"`.

> **After:** The character after `"/admin"` is `"-"`, so `withoutBase` returns `"/admin-dashboard"` unchanged. `"/admin/dashboard"` still becomes `"/dashboard"`.

A Nuxt app is served under `baseURL: '/admin/'` and has a page called `/admin-dashboard` (nuxt/nuxt#33924). Before routing, the framework asks `withoutBase` to strip the base so it can look the page up. The path that comes back decides which page renders. Before this change, the answer was `"/-dashboard"`, a page that does not exist.

The path `"/admin-dashboard"` reaches `withoutBase` with the base `"/admin/"`. [`withoutTrailingSlash` trims the base](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L322) to `"/admin"`, and [the `startsWith` test](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L323-L325) passes, because the string does begin with those six characters. Both versions agree up to this point.

They part at the next step. The new code [looks at the character just past the base](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L327), `input[6]`, which is `"-"`. Under [the new guard](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L328-L330), the base only counts if that character is missing, `"/"`, or `"?"`. A `"-"` means `"/admin"` was just the start of a longer segment name, so `withoutBase` returns `"/admin-dashboard"` as it came in.

The old code had no such check. After the prefix test it went straight to [slicing off six characters](https://github.com/unjs/ufo/blob/5fb179d51384301ffb66b48e213863a27cadd1ff/src/utils.ts#L322-L323). That left `"-dashboard"`, and it then added a leading slash to make `"/-dashboard"`. The test failed with `expected '/-dashboard' to be '/admin-dashboard'`. The base `"/admin"`, written without the trailing slash, followed the same path and produced the same failure.

The two genuine matches in this group behave as they did before. In `"/admin/dashboard"` the character after the base is `"/"`, so the guard lets it through to [the existing slice](https://github.com/unjs/ufo/blob/cb6af4e5e55fc21b5b776fd13b2d1e372f71f40c/src/utils.ts#L331-L332), which returns `"/dashboard"`. `"/admin/admin-dashboard"` returns `"/admin-dashboard"`. Only the first segment is compared against the base, so a later segment that also starts with `admin` is left alone.

> **For the reviewer:** The new rule is that a base matches only at a segment boundary, and only `"/"`, `"?"` and the end of the string count as a boundary. `"#"` is not on that list. Reading the code, `withoutBase("/admin#top", "/admin")` now returns `"/admin#top"` unchanged, where the old code returned `"/#top"`. No test covers this case. Ask the author whether a fragment directly after the base should count as a boundary, and request a test either way.

> **For the reviewer:** Any caller that relied on the loose prefix match will get different output now. One example is a base like `"/v1"` used to strip the start of `"/v1beta/..."`. That old behaviour was a bug, but it changes what callers see, so mention it in the release notes.

With this change, `withoutBase` treats the base as a whole path segment rather than as leading characters, which is what a router needs from it.
