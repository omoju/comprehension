import { describe, it, expect } from "vitest";
import { withoutBase } from "../../../src";

// Chapter 3: withoutBase — cases that are preserved across the change.
// Each assertion holds on BOTH the base and the head: the new nextChar
// guard runs on the genuine-prefix cases but never alters their result,
// because the character after the base is '/', '?', or absent.
describe("withoutBase preserved behaviour (PR #313, chapter 3)", () => {
  it("returns the input untouched when the base is empty ('/')", () => {
    expect(withoutBase("/test/", "/")).toBe("/test/");
    expect(withoutBase("/?test", "/")).toBe("/?test");
    expect(withoutBase("https://test.com", "/")).toBe("https://test.com");
  });

  it("returns the input untouched when it does not start with the base", () => {
    expect(withoutBase("/bar", "/foo")).toBe("/bar");
    expect(withoutBase("/", "/foo")).toBe("/");
    expect(withoutBase("https://test.com", "/base/")).toBe("https://test.com");
  });

  it("still trims a genuine prefix ending on a '/' boundary", () => {
    expect(withoutBase("/base/a", "/base")).toBe("/a");
    expect(withoutBase("/base/a", "/base/")).toBe("/a");
  });

  it("still trims a prefix that ends at end-of-string", () => {
    expect(withoutBase("/base", "/base/")).toBe("/");
    expect(withoutBase("/base/", "/base")).toBe("/");
    expect(withoutBase("/base/a", "/base/a/")).toBe("/");
  });

  it("still respects the '?' query boundary", () => {
    expect(withoutBase("/api?test", "/api")).toBe("/?test");
  });
});
