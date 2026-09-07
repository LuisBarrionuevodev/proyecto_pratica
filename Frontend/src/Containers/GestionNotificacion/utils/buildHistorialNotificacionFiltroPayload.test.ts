import { describe, expect, it } from "vitest";
import {
  buildHistorialNotificacionFiltroPayload,
  historialNotificacionHasPeriodChosen,
  historialNotificacionHasSpecificSearch,
  historialPayloadToExpedienteCall,
} from "./buildHistorialNotificacionFiltroPayload";

const MOTIVOS_CATALOG = [
  { id: 10, nombre: "FALTA DE HABILITACION" },
  { id: 20, nombre: "HIGIENE" },
];

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
  motivoId: "" as const,
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

  it("motivo seleccionado sin combinar es global y envía motivo_id", () => {
    const r = buildHistorialNotificacionFiltroPayload(
      {
        ...emptyForm,
        mes: 7,
        anio: 2026,
        motivoId: 10,
      },
      MOTIVOS_CATALOG
    );
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.payload.period.kind).toBe("global");
      expect(r.payload.motivoId).toBe(10);
      expect(r.payload.motivoNombre).toBe("FALTA DE HABILITACION");
    }
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

  it("detecta búsqueda específica por motivo_id", () => {
    expect(historialNotificacionHasSpecificSearch({ ...emptyForm, motivoId: 10 })).toBe(true);
    expect(historialNotificacionHasSpecificSearch(emptyForm)).toBe(false);
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
    expect(call.opts.page).toBe(1);
    expect(call.opts.pageSize).toBe(10);
  });

  it("motivo_id en opts, no motivo_q", () => {
    const r = buildHistorialNotificacionFiltroPayload(
      { ...emptyForm, motivoId: 20 },
      MOTIVOS_CATALOG
    );
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    const call = historialPayloadToExpedienteCall(r.payload);
    expect(call.opts.motivoId).toBe(20);
    expect(call.opts).not.toHaveProperty("motivoQ");
  });

  it("paginación server-side en opts", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 3,
      anio: 2025,
    });
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    const call = historialPayloadToExpedienteCall(r.payload, { page: 2, pageSize: 10 });
    expect(call.opts.page).toBe(2);
    expect(call.opts.pageSize).toBe(10);
  });

  it("export sin paginación cuando includePagination es false", () => {
    const r = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 3,
      anio: 2025,
    });
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    const call = historialPayloadToExpedienteCall(r.payload, undefined, { includePagination: false });
    expect(call.opts.page).toBeUndefined();
    expect(call.opts.pageSize).toBeUndefined();
  });
});
