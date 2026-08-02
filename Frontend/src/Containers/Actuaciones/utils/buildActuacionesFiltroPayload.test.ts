import { describe, expect, it } from "vitest";
import {
  actuacionesBusquedaEspecificaValida,
  buildActuacionesExportFiltersFromMeta,
  buildActuacionesFiltroPayload,
} from "./buildActuacionesFiltroPayload";

const baseForm = {
  desde: "2026-01-01",
  hasta: "2026-01-31",
  tipo: "INSPECCION",
  contraproducencia: "LOCAL CERRADO",
  busquedaEspecifica: "",
  combinarConRango: false,
};

describe("buildActuacionesFiltroPayload", () => {
  it("envía solo rango y catálogos cuando no hay búsqueda específica", () => {
    expect(buildActuacionesFiltroPayload(baseForm)).toEqual({
      desde: "2026-01-01",
      hasta: "2026-01-31",
      tipo: "INSPECCION",
      contraproducencia: "LOCAL CERRADO",
      orden_trabajo: null,
      actuacion_id: null,
      q: null,
    });
  });

  it("omite rango y catálogos en búsqueda específica sin combinar", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...baseForm,
        busquedaEspecifica: " 123456 ",
      })
    ).toEqual({
      desde: null,
      hasta: null,
      tipo: null,
      contraproducencia: null,
      orden_trabajo: null,
      actuacion_id: null,
      q: "123456",
    });
  });

  it("combina rango cuando el usuario lo indica", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...baseForm,
        busquedaEspecifica: "Corrientes",
        combinarConRango: true,
      })
    ).toEqual({
      desde: "2026-01-01",
      hasta: "2026-01-31",
      tipo: "INSPECCION",
      contraproducencia: "LOCAL CERRADO",
      orden_trabajo: null,
      actuacion_id: null,
      q: "Corrientes",
    });
  });

  it("no envía q con menos de 2 caracteres", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...baseForm,
        busquedaEspecifica: "1",
      })
    ).toMatchObject({ q: null, desde: "2026-01-01" });
  });

  it("no usa orden_trabajo en el payload", () => {
    const payload = buildActuacionesFiltroPayload({
      ...baseForm,
      busquedaEspecifica: "000042",
    });
    expect(payload.orden_trabajo).toBeNull();
    expect(payload.q).toBe("000042");
  });
});

describe("actuacionesBusquedaEspecificaValida", () => {
  it("exige al menos 2 caracteres", () => {
    expect(actuacionesBusquedaEspecificaValida("a")).toBe(false);
    expect(actuacionesBusquedaEspecificaValida("ab")).toBe(true);
  });
});

describe("buildActuacionesExportFiltersFromMeta", () => {
  it("combina q con rango cuando meta los trae juntos", () => {
    expect(
      buildActuacionesExportFiltersFromMeta({
        total: 2,
        page: 1,
        page_size: 50,
        desde: "2026-01-01",
        hasta: "2026-01-31",
        tipo: "INSPECCION",
        contraproducencia: null,
        orden_trabajo: null,
        q: "acta",
      })
    ).toMatchObject({
      q: "acta",
      desde: "2026-01-01",
      hasta: "2026-01-31",
      tipo: "INSPECCION",
    });
  });
});
