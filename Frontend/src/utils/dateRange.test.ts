import { afterEach, describe, expect, it, vi } from "vitest";

import {
  formatOperativoPeriodoLabel,
  getCurrentMonthRange,
  getOperativoMonthToDateRange,
} from "./dateRange";

describe("dateRange — operativo mensual", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("getOperativoMonthToDateRange usa 1.er día del mes → hoy (2026-09-13)", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    expect(getOperativoMonthToDateRange()).toEqual({
      desde: "2026-09-01",
      hasta: "2026-09-13",
    });
  });

  it("getCurrentMonthRange sigue usando fin de mes completo", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    expect(getCurrentMonthRange()).toEqual({
      desde: "2026-09-01",
      hasta: "2026-09-30",
    });
  });

  it("formatOperativoPeriodoLabel formatea DD/MM/YYYY", () => {
    expect(formatOperativoPeriodoLabel("2026-09-01", "2026-09-13")).toBe("01/09/2026 — 13/09/2026");
  });
});
