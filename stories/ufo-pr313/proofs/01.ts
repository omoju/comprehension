import { describe, it, expect } from "vitest";
import { withoutBase } from "../../../src";

describe("withoutBase only strips the base at a segment boundary", () => {
  it("leaves /admin-dashboard intact when the base is /admin/", () => {
    expect(withoutBase("/admin-dashboard", "/admin/")).toBe("/admin-dashboard");
  });

  it("leaves /admin-dashboard intact when the base is /admin", () => {
    expect(withoutBase("/admin-dashboard", "/admin")).toBe("/admin-dashboard");
  });

  it("still strips a real base followed by a slash", () => {
    expect(withoutBase("/admin/dashboard", "/admin/")).toBe("/dashboard");
    expect(withoutBase("/admin/admin-dashboard", "/admin/")).toBe(
      "/admin-dashboard",
    );
  });
});
