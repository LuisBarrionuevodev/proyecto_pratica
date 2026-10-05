import { afterEach, describe, expect, it, vi } from "vitest";

import { buildIndicadoresFiltrosEfectivos, resolveIndicadoresDateRange } from "./indicadoresEffectiveFilters";

describe("indicadoresEffectiveFilters", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("override mensual tiene prioridad sobre tab Mensual", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 4, 12, 0, 0));

    const range = resolveIndicadoresDateRange({
      periodo: "Mensual",
      monthOverride: { year: 2026, month: 7 },
    });
    expect(range.desde).toBe("2026-07-01");
    expect(range.hasta).toBe("2026-07-31");
    expect(range.monthOverrideActive).toBe(true);
    expect(range.periodoUiLabel).toBe("Julio 2026");
  });

  it("sin override usa tab activo", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    const range = resolveIndicadoresDateRange({
      periodo: "Mensual",
      monthOverride: null,
    });
    expect(range.desde).toBe("2026-09-01");
    expect(range.hasta).toBe("2026-09-13");
    expect(range.monthOverrideActive).toBe(false);
  });

  it("buildIndicadoresFiltrosEfectivos omite ids vacíos y respeta inspector scope flag", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    const admin = buildIndicadoresFiltrosEfectivos({
      periodo: "Semanal",
      monthOverride: null,
      distritoId: "3",
      inspectorId: "",
      isInspectorIndicadores: false,
    });
    expect(admin.distrito_id).toBe(3);
    expect(admin.inspector_id).toBeUndefined();

    const insp = buildIndicadoresFiltrosEfectivos({
      periodo: "Semanal",
      monthOverride: null,
      distritoId: "3",
      inspectorId: "9",
      isInspectorIndicadores: true,
    });
    expect(insp.distrito_id).toBeUndefined();
    expect(insp.inspector_id).toBeUndefined();
  });
});
