import { describe, it, expect } from "vitest";
import { withBase } from "../../../src";

// Chapter 1: the ten withBase cases that must behave identically
// before and after the change. These all pass on head AND base.
describe("withBase — preserved cases (ch.1)", () => {
  const cases: Array<{ base: string; input: string; out: string }> = [
    { base: "/", input: "/", out: "/" },
    { base: "/foo", input: "", out: "/foo" },
    { base: "/foo/", input: "/", out: "/foo" },
    { base: "/foo", input: "/bar", out: "/foo/bar" },
    { base: "/base/", input: "/base", out: "/base" },
    { base: "/base", input: "/base/", out: "/base/" },
    { base: "/base", input: "/base/a", out: "/base/a" },
    { base: "/base/", input: "/base/a", out: "/base/a" },
    { base: "/base/", input: "https://test.com", out: "https://test.com" },
    { base: "/", input: "https://test.com", out: "https://test.com" },
  ];

  for (const c of cases) {
    it(`${JSON.stringify(c.base)} + ${JSON.stringify(c.input)} => ${c.out}`, () => {
      expect(withBase(c.input, c.base)).toBe(c.out);
    });
  }

  it("a genuine prefix with an absent next char still returns the input", () => {
    // _base = "/base", input[5] is undefined -> early return keeps input
    expect(withBase("/base", "/base/")).toBe("/base");
  });

  it("a genuine prefix with a '/' next char still returns the input", () => {
    // _base = "/base", input[5] is "/" -> early return keeps input
    expect(withBase("/base/a", "/base")).toBe("/base/a");
  });
});
