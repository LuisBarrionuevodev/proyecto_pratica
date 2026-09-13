/** @jsxImportSource react */
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { getOperativoMonthToDateRange } from "../../utils/dateRange";
import { periodoToDateRange } from "../Dashboard/utils/periodoDateRange";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-ANALYTICS.4.1 — rango default Mapa", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("MapPage usa getOperativoMonthToDateRange como default", () => {
    const src = read("src/Containers/Mapa/MapPage.tsx");
    expect(src).toContain("getOperativoMonthToDateRange");
    expect(src).not.toContain("getCurrentMonthRange");
  });

  it("MapPage no muestra OperativoPeriodoLabel (rango en inputs Desde/Hasta)", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).not.toContain("OperativoPeriodoLabel");
  });

  it("Dashboard conserva OperativoPeriodoLabel", () => {
    const panel = read("src/Containers/Dashboard/Components/Panel.tsx");
    expect(panel).toContain("OperativoPeriodoLabel");
  });

  it("2026-09-13: default Dashboard Mensual == default Mapa", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    expect(periodoToDateRange("Mensual")).toEqual(getOperativoMonthToDateRange());
  });
});
