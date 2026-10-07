import { describe, it, expect } from "vitest";
import { withoutBase } from "../../../src";

describe("withoutBase still strips genuine base matches", () => {
  it("strips the base when a query string follows it directly", () => {
    expect(withoutBase("/api?test", "/api")).toBe("/?test");
  });

  it("strips the base at a path segment boundary", () => {
    expect(withoutBase("/base/a", "/base")).toBe("/a");
    expect(withoutBase("/base/a", "/base/")).toBe("/a");
    expect(withoutBase("/base/", "/base")).toBe("/");
  });

  it("collapses an input equal to the base to the root", () => {
    expect(withoutBase("/base", "/base/")).toBe("/");
    expect(withoutBase("/base/a", "/base/a/")).toBe("/");
  });

  it("leaves inputs alone for a root base or a non-matching base", () => {
    expect(withoutBase("/test/", "/")).toBe("/test/");
    expect(withoutBase("/?test", "/")).toBe("/?test");
    expect(withoutBase("/bar", "/foo")).toBe("/bar");
    expect(withoutBase("https://test.com", "/base/")).toBe("https://test.com");
  });
});
