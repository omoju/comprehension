import { describe, it, expect } from "vitest";
import { withBase } from "../../../src";

describe("withBase leaves inputs that already carry the base alone", () => {
  it("returns an input equal to the trimmed base unchanged", () => {
    expect(withBase("/base", "/base/")).toBe("/base");
  });

  it("returns inputs with '/' right after the base unchanged", () => {
    expect(withBase("/base/", "/base")).toBe("/base/");
    expect(withBase("/base/a", "/base")).toBe("/base/a");
    expect(withBase("/base/a", "/base/")).toBe("/base/a");
  });

  it("still joins inputs that do not start with the base", () => {
    expect(withBase("/bar", "/foo")).toBe("/foo/bar");
    expect(withBase("", "/foo")).toBe("/foo");
    expect(withBase("/", "/foo/")).toBe("/foo");
  });

  it("still exits early for root bases and protocol URLs", () => {
    expect(withBase("/", "/")).toBe("/");
    expect(withBase("https://test.com", "/base/")).toBe("https://test.com");
    expect(withBase("https://test.com", "/")).toBe("https://test.com");
  });
});
