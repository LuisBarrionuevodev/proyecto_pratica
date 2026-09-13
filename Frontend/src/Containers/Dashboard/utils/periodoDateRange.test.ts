import { afterEach, describe, expect, it, vi } from "vitest";

import { periodoToDateRange } from "./periodoDateRange";

describe("periodoToDateRange", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("Mensual alinea con getOperativoMonthToDateRange (2026-09-13)", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    expect(periodoToDateRange("Mensual")).toEqual({
      desde: "2026-09-01",
      hasta: "2026-09-13",
    });
  });

  it("con registros 13/14/30, Mensual al 13 solo incluye hasta el 13", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    const { desde, hasta } = periodoToDateRange("Mensual");
    expect(desde).toBe("2026-09-01");
    expect(hasta).toBe("2026-09-13");
    expect(hasta).not.toBe("2026-09-30");
  });
});
