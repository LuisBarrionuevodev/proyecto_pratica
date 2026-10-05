import { afterEach, describe, expect, it, vi } from "vitest";

import {
  formatIndicadoresMonthYearLabel,
  isFutureIndicadoresMonth,
  monthYearToIndicadoresDateRange,
} from "./indicadoresMonthYearRange";

describe("indicadoresMonthYearRange", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("mes histórico: primer y último día del mes", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 4, 12, 0, 0));

    expect(monthYearToIndicadoresDateRange({ year: 2026, month: 8 })).toEqual({
      desde: "2026-08-01",
      hasta: "2026-08-31",
    });
  });

  it("mes actual termina hoy", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 4, 12, 0, 0));

    expect(monthYearToIndicadoresDateRange({ year: 2026, month: 10 })).toEqual({
      desde: "2026-10-01",
      hasta: "2026-10-04",
    });
  });

  it("detecta meses futuros", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 4, 12, 0, 0));

    expect(isFutureIndicadoresMonth(2026, 11)).toBe(true);
    expect(isFutureIndicadoresMonth(2027, 1)).toBe(true);
    expect(isFutureIndicadoresMonth(2026, 10)).toBe(false);
    expect(isFutureIndicadoresMonth(2026, 9)).toBe(false);
  });

  it("formatea etiqueta de mes", () => {
    expect(formatIndicadoresMonthYearLabel({ year: 2026, month: 10 })).toBe("Octubre 2026");
  });
});
