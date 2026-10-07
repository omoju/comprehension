import { describe, it, expect } from "vitest";
import { withBase } from "../../../src";

describe("withBase · false prefix is no longer treated as having the base", () => {
  it("prepends the base when the match is not on a segment boundary (trailing-slash base)", () => {
    // base run returns "/admin-dashboard" (base dropped); head returns "/admin/admin-dashboard"
    expect(withBase("/admin-dashboard", "/admin/")).toBe("/admin/admin-dashboard");
  });

  it("prepends the base when the match is not on a segment boundary (no-trailing-slash base)", () => {
    // base run returns "/admin-dashboard"; head returns "/admin/admin-dashboard"
    expect(withBase("/admin-dashboard", "/admin")).toBe("/admin/admin-dashboard");
  });

  it("still leaves a genuine '/' boundary prefix untouched (unchanged by the fix)", () => {
    expect(withBase("/admin/admin-dashboard", "/admin/")).toBe("/admin/admin-dashboard");
    expect(withBase("/admin/dashboard", "/admin/")).toBe("/admin/dashboard");
  });
});
