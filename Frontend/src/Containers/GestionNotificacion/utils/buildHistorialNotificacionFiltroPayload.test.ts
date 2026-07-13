import { describe, expect, it } from "vitest";
import {
  buildHistorialNotificacionFiltroPayload,
  historialNotificacionHasPeriodChosen,
  historialNotificacionHasSpecificSearch,
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

  it("requiere criterio de búsqueda o período", () => {
    const r = buildHistorialNotificacionFiltroPayload(emptyForm);
    expect(r.ok).toBe(false);
  });

  it("detecta búsqueda específica por contribuyente", () => {
    expect(
      historialNotificacionHasSpecificSearch({ ...emptyForm, contribuyenteQ: "Pérez" })
    ).toBe(true);
  });
});
