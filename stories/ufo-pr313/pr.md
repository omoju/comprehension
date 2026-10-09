# fix(withBase, withoutBase): prevent false prefix matches

Resolves: https://github.com/nuxt/nuxt/issues/33924

## Summary

While investigating [nuxt/nuxt#33924](https://github.com/nuxt/nuxt/issues/33924), I found that `withoutBase` was being a bit too eager when stripping base URLs.

**The issue:** When using `baseURL: '/admin/'` with a page like `/admin-dashboard`, the function incorrectly stripped `/admin` because it only checked `startsWith()` without verifying that the match ends at a path segment boundary.

```js
withoutBase("/admin-dashboard", "/admin/")
// Before: "/-dashboard" ❌
// After:  "/admin-dashboard" ✅
```

The fix: Added a simple check to ensure the character after the base is either /, ?, or end of string before treating it as a valid base match.

Test plan

- Added test cases for the bug
- All existing tests pass

### Update ⚠️
Same issue is in `withBase` as well. I also fixed it and added new tests.
