import { describe, expect, it } from "vitest";
import {
  buildHistorialNotificacionFiltroPayload,
  historialNotificacionHasPeriodChosen,
  historialNotificacionHasSpecificSearch,
  historialPayloadToExpedienteCall,
} from "./buildHistorialNotificacionFiltroPayload";

const emptyForm = {
  periodMode: "month" as const,
  mes: "" as const,
  anio: "" as const,
  desde: null,
  hasta: null,
  distritoId: "" as const,
  numeroNotificacion: "",
  calleQ: "",
  contribuyenteQ: "",
  motivoQ: "",
  combinarConPeriodo: false,
};

describe("buildHistorialNotificacionFiltroPayload", () => {
  it("inicia sin período elegido", () => {
    expect(historialNotificacionHasPeriodChosen(emptyForm)).toBe(false);
  });

  it("búsqueda por N° notificación no envía mes/año", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 7,
      anio: 2026,
      numeroNotificacion: "123456",
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.payload.period).toEqual({ kind: "global" });
      expect(r.payload.numeroNotificacion).toBe("123456");
    }
  });

  it("motivo/infracción sin combinar es global", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 7,
      anio: 2026,
      motivoQ: "higiene",
    });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.payload.period.kind).toBe("global");
  });

  it("mes/año elegidos se envían sin búsqueda específica", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 3,
      anio: 2025,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.payload.period).toEqual({ kind: "month", mes: 3, anio: 2025 });
    }
  });

  it("combina período si el usuario lo indica", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 7,
      anio: 2026,
      calleQ: "Corrientes",
      combinarConPeriodo: true,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.payload.period).toEqual({ kind: "month", mes: 7, anio: 2026 });
      expect(r.payload.calleQ).toBe("Corrientes");
    }
  });

  it("requiere criterio de búsqueda, período o distrito", () => {
    const r = buildHistorialNotificacionFiltroPayload(emptyForm);
    expect(r.ok).toBe(false);
  });

  it("permite filtrar solo por distrito", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      distritoId: 3,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.payload.period.kind).toBe("global");
      expect(r.payload.distritoId).toBe(3);
    }
  });

  it("detecta búsqueda específica por contribuyente", () => {
    expect(
      historialNotificacionHasSpecificSearch({ ...emptyForm, contribuyenteQ: "Pérez" })
    ).toBe(true);
  });
});

describe("historialPayloadToExpedienteCall", () => {
  it("mes/anio no convierte a desde/hasta", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 3,
      anio: 2025,
    });
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    const call = historialPayloadToExpedienteCall(r.payload);
    expect(call.desde).toBeUndefined();
    expect(call.hasta).toBeUndefined();
    expect(call.opts.mes).toBe(3);
    expect(call.opts.anio).toBe(2025);
  });

  it("global con número de notificación usa omitir_rango_fecha", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      numeroNotificacion: "123456",
    });
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    const call = historialPayloadToExpedienteCall(r.payload);
    expect(call.opts.omitirRangoFecha).toBe(true);
    expect(call.opts.numeroNotificacion).toBe("123456");
  });
});
