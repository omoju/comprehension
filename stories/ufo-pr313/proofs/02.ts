import { describe, it, expect } from "vitest";
import { withBase } from "../../../src";

describe("withBase only treats the base as present at a segment boundary", () => {
  it("prefixes /admin-dashboard under base /admin/", () => {
    expect(withBase("/admin-dashboard", "/admin/")).toBe("/admin/admin-dashboard");
  });

  it("prefixes /admin-dashboard under base /admin", () => {
    expect(withBase("/admin-dashboard", "/admin")).toBe("/admin/admin-dashboard");
  });

  it("still leaves inputs that genuinely carry the base untouched", () => {
    expect(withBase("/admin/dashboard", "/admin/")).toBe("/admin/dashboard");
    expect(withBase("/admin/admin-dashboard", "/admin/")).toBe(
      "/admin/admin-dashboard",
    );
  });
});
