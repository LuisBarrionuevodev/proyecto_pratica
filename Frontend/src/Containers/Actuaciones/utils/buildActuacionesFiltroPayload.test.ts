import { describe, expect, it } from "vitest";
import {
  ACTUACIONES_FILTRO_FORM_VACIO,
  buildActuacionesExportFiltersFromMeta,
  buildActuacionesFiltroPayload,
  resolveActuacionesPeriod,
  validateActuacionesFiltroForm,
} from "./buildActuacionesFiltroPayload";

describe("buildActuacionesFiltroPayload — período PERF.1-A1.1", () => {
  it("P1 — solo mes/año → desde/hasta del mes", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        periodMode: "month",
        mes: 8,
        anio: 2026,
      })
    ).toMatchObject({
      desde: "2026-08-01",
      hasta: "2026-08-31",
    });
  });

  it("P2 — solo rango", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        periodMode: "range",
        desde: "2026-08-10",
        hasta: "2026-08-25",
      })
    ).toMatchObject({
      desde: "2026-08-10",
      hasta: "2026-08-25",
    });
  });

  it("P3 — solo período es válido", () => {
    const result = validateActuacionesFiltroForm({
      ...ACTUACIONES_FILTRO_FORM_VACIO,
      periodMode: "month",
      mes: 8,
      anio: 2026,
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.desde).toBe("2026-08-01");
      expect(result.payload.hasta).toBe("2026-08-31");
    }
  });

  it("P4 — solo OT sin período", () => {
    const payload = buildActuacionesFiltroPayload({
      ...ACTUACIONES_FILTRO_FORM_VACIO,
      ordenTrabajo: "092834",
    });
    expect(payload).toMatchObject({
      orden_trabajo: "092834",
      q: null,
    });
    expect(payload.desde).toBeUndefined();
    expect(payload.hasta).toBeUndefined();
  });

  it("P5 — inspector + mes/año", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        periodMode: "month",
        mes: 8,
        anio: 2026,
        inspectorId: 12,
      })
    ).toMatchObject({
      inspector_id: 12,
      desde: "2026-08-01",
      hasta: "2026-08-31",
    });
  });

  it("P6 — específico + rango", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        periodMode: "range",
        desde: "2026-01-01",
        hasta: "2026-06-30",
        documentoQ: "42006775",
      })
    ).toMatchObject({
      documento_q: "42006775",
      desde: "2026-01-01",
      hasta: "2026-06-30",
    });
  });

  it("P7 — rango inválido (desde > hasta)", () => {
    const result = validateActuacionesFiltroForm({
      ...ACTUACIONES_FILTRO_FORM_VACIO,
      periodMode: "range",
      desde: "2026-08-30",
      hasta: "2026-08-10",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/desde/i);
    }
  });

  it("P8 — cambio de modo no mezcla payloads", () => {
    const monthForm = {
      ...ACTUACIONES_FILTRO_FORM_VACIO,
      periodMode: "month" as const,
      mes: 8,
      anio: 2026,
      desde: "2026-01-01",
      hasta: "2026-01-31",
    };
    expect(resolveActuacionesPeriod(monthForm)).toEqual({
      desde: "2026-08-01",
      hasta: "2026-08-31",
    });

    const rangeForm = {
      ...ACTUACIONES_FILTRO_FORM_VACIO,
      periodMode: "range" as const,
      mes: 8,
      anio: 2026,
      desde: "2026-08-10",
      hasta: "2026-08-25",
    };
    expect(resolveActuacionesPeriod(rangeForm)).toEqual({
      desde: "2026-08-10",
      hasta: "2026-08-25",
    });
    expect(buildActuacionesFiltroPayload(rangeForm).desde).toBe("2026-08-10");
  });
});

describe("buildActuacionesFiltroPayload — filtros específicos PERF.1-A1", () => {
  it("OT usa orden_trabajo, no q", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        ordenTrabajo: "092834",
      })
    ).toMatchObject({ orden_trabajo: "092834", q: null });
  });

  it("acta comprobación", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        actaComprobacion: "1234",
      })
    ).toMatchObject({ acta_comprobacion: "1234" });
  });

  it("no envía calle_q con menos de 2 caracteres", () => {
    expect(
      buildActuacionesFiltroPayload({
        ...ACTUACIONES_FILTRO_FORM_VACIO,
        calleQ: "a",
        periodMode: "range",
        desde: "2026-01-01",
        hasta: "2026-01-31",
      }).calle_q
    ).toBeUndefined();
  });
});

describe("buildActuacionesExportFiltersFromMeta", () => {
  it("usa anchor filters de meta", () => {
    expect(
      buildActuacionesExportFiltersFromMeta({
        total: 2,
        page: 1,
        page_size: 50,
        desde: "2026-01-01",
        hasta: "2026-01-31",
        tipo: "INSPECCION",
        contraproducencia: null,
        orden_trabajo: "092834",
      })
    ).toMatchObject({
      orden_trabajo: "092834",
      desde: "2026-01-01",
    });
  });
});
