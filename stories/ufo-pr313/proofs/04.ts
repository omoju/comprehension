import { describe, it, expect } from "vitest";
import { withoutBase } from "../../../src";

describe("withoutBase stops mangling a false prefix (PR #313, ch.4)", () => {
  it("returns a false-prefix path unchanged instead of /-dashboard (trailing-slash base)", () => {
    // base run produced "/-dashboard"; head returns the input whole
    expect(withoutBase("/admin-dashboard", "/admin/")).toBe("/admin-dashboard");
  });

  it("returns a false-prefix path unchanged instead of /-dashboard (bare base)", () => {
    expect(withoutBase("/admin-dashboard", "/admin")).toBe("/admin-dashboard");
  });

  it("still never yields the old mangled form", () => {
    expect(withoutBase("/admin-dashboard", "/admin/")).not.toBe("/-dashboard");
  });

  it("still trims a genuine prefix at a slash boundary", () => {
    expect(withoutBase("/admin/admin-dashboard", "/admin/")).toBe(
      "/admin-dashboard",
    );
    expect(withoutBase("/admin/dashboard", "/admin/")).toBe("/dashboard");
  });
});
