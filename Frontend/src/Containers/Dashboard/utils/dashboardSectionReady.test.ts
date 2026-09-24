import { describe, expect, it } from "vitest";

import { isDashboardSectionReady } from "./dashboardSectionReady";

describe("isDashboardSectionReady", () => {
  it("es true con datos", () => {
    expect(isDashboardSectionReady({ foo: 1 }, null)).toBe(true);
  });

  it("es true con error", () => {
    expect(isDashboardSectionReady(null, "falló")).toBe(true);
  });

  it("es false sin datos ni error", () => {
    expect(isDashboardSectionReady(null, null)).toBe(false);
    expect(isDashboardSectionReady(undefined, "")).toBe(false);
  });
});
