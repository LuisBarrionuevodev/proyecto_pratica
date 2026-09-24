/** @jsxImportSource react */
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { getOperativoMonthToDateRange } from "../../utils/dateRange";
import {
  mapaEjecucionQueryValue,
  mapaMotivoQueryValue,
  mapaOrigenQueryValue,
  mapaRealizadosRubroQueryValue,
  mapaRealizadosTipoQueryValue,
} from "./constants/mapaOperativo";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

function buildResetQueryParams() {
  const range = getOperativoMonthToDateRange();
  return {
    desde: range.desde,
    hasta: range.hasta,
    distrito_id: undefined,
    tipo: undefined,
    inspector_id: undefined,
    rubro_id: undefined,
    ejecucion: mapaEjecucionQueryValue("TODOS"),
    origen: mapaOrigenQueryValue("TODOS"),
    motivo_no_realizado: mapaMotivoQueryValue("TODAS"),
  };
}

describe("OPER-ANALYTICS-FILTERS.2 — Mapa filtros UX", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("label Motivo no realizado (no Contraproducencia)", () => {
    const filtro = read("src/Containers/Mapa/Components/MapaFiltrosUnificados.tsx");
    expect(filtro).toContain('label="Motivo no realizado"');
    expect(filtro).not.toContain('label="Contraproducencia"');
  });

  it("deshabilita motivo si ejecución REALIZADO y tipo si no es REALIZADO", () => {
    const filtro = read("src/Containers/Mapa/Components/MapaFiltrosUnificados.tsx");
    expect(filtro).toContain('const motivoDisabled = ejecucion === "REALIZADO"');
    expect(filtro).toContain('const tipoDisabled = ejecucion !== "REALIZADO"');
    expect(filtro).toContain("disabled={tipoDisabled}");
  });

  it("MapPage resetea motivo/tipo al cambiar ejecución", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain('patch.motivoNoRealizado = "TODAS"');
    expect(mapPage).toContain('patch.realizadoTipoIniciador = "TODOS"');
    expect(mapPage).toContain("handleLimpiarFiltros");
    expect(mapPage).toContain("onLimpiar={handleLimpiarFiltros}");
  });

  it("Limpiar filtros restaura defaults month-to-date y TODOS", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 13, 12, 0, 0));

    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("getOperativoMonthToDateRange()");
    expect(mapPage).toContain('ejecucion: "TODOS"');
    expect(mapPage).toContain('origen: "TODOS"');
    expect(mapPage).toContain('motivoNoRealizado: "TODAS"');
    expect(mapPage).toContain('realizadoTipoIniciador: "TODOS"');

    const expected = buildResetQueryParams();
    expect(expected.desde).toBe("2026-09-01");
    expect(expected.hasta).toBe("2026-09-13");
    expect(expected.ejecucion).toBe("TODOS");
    expect(expected.origen).toBeUndefined();
    expect(expected.motivo_no_realizado).toBeUndefined();
    expect(expected.tipo).toBeUndefined();
    expect(expected.rubro_id).toBeUndefined();
    expect(expected.distrito_id).toBeUndefined();
    expect(expected.inspector_id).toBeUndefined();
  });

  it("useMapaOperativo no envía tipo si ejecución != REALIZADO", () => {
    const hook = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(hook).toContain('ejecucionNorm === "REALIZADO"');
    expect(hook).toContain("mapaRealizadosTipoQueryValue(p.tipo) : undefined");

    expect(mapaRealizadosTipoQueryValue("INSPECCION")).toBe("INSPECCION");
    const reset = buildResetQueryParams();
    expect(reset.tipo).toBeUndefined();
    expect(mapaRealizadosRubroQueryValue("")).toBeUndefined();
  });

  it("botón Limpiar filtros en panel de filtros (primary)", () => {
    const filtro = read("src/Containers/Mapa/Components/MapaFiltrosUnificados.tsx");
    expect(filtro).toContain("Limpiar filtros");
    expect(filtro).toContain('data-testid="mapa-realizados-limpiar-filtros"');
    const limpiarIdx = filtro.indexOf('data-testid="mapa-realizados-limpiar-filtros"');
    expect(filtro.slice(Math.max(0, limpiarIdx - 160), limpiarIdx)).toContain('dsVariant="primary"');
  });
});
