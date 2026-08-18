import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./actuacionesPendientesApi", () => ({
  getActuacionesPendientesExpediente: vi.fn(async () => ({
    items: [],
    meta: { total: 0, source_type: "notificacion", desde: null, hasta: null },
  })),
  getPendientesReinspeccionNotificacion: vi.fn(async () => []),
}));

import { getActuacionesPendientesExpediente } from "./actuacionesPendientesApi";
import { fetchAllNotificacionesForExport } from "./notificacionesExportApi";
import type { HistorialNotificacionFiltroPayload } from "../Containers/GestionNotificacion/utils/buildHistorialNotificacionFiltroPayload";

describe("FILTROS-2 fetchAllNotificacionesForExport historial", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("con payload mes/anio aplicado manda mes y anio sin desde/hasta del diálogo", async () => {
    const payload: HistorialNotificacionFiltroPayload = {
      period: { kind: "month", mes: 4, anio: 2025 },
      distritoId: 2,
    };

    await fetchAllNotificacionesForExport({
      desde: "2020-01-01",
      hasta: "2020-01-31",
      plazoSlice: "total",
      historialAppliedPayload: payload,
    });

    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "notificacion",
      2,
      expect.objectContaining({ mes: 4, anio: 2025 })
    );
    const opts = vi.mocked(getActuacionesPendientesExpediente).mock.calls[0]?.[4];
    expect(opts?.omitirRangoFecha).toBeUndefined();
  });

  it("con payload rango desde/hasta reenvía fechas del historial", async () => {
    const payload: HistorialNotificacionFiltroPayload = {
      period: { kind: "range", desde: "2026-02-01", hasta: "2026-02-28" },
      distritoId: null,
    };

    await fetchAllNotificacionesForExport({
      desde: "2020-01-01",
      hasta: "2020-01-31",
      plazoSlice: "total",
      historialAppliedPayload: payload,
    });

    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      "2026-02-01",
      "2026-02-28",
      "notificacion",
      null,
      expect.any(Object)
    );
  });

  it("búsqueda global sin período exporta con omitir_rango_fecha", async () => {
    const payload: HistorialNotificacionFiltroPayload = {
      period: { kind: "global" },
      distritoId: null,
      numeroNotificacion: "123456",
    };

    await fetchAllNotificacionesForExport({
      desde: "2020-01-01",
      hasta: "2020-01-31",
      plazoSlice: "total",
      historialAppliedPayload: payload,
    });

    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "notificacion",
      null,
      expect.objectContaining({
        omitirRangoFecha: true,
        numeroNotificacion: "123456",
      })
    );
  });

  it("conserva filtros documentales y distrito", async () => {
    const payload: HistorialNotificacionFiltroPayload = {
      period: { kind: "global" },
      distritoId: 3,
      calleQ: "Corrientes",
      contribuyenteQ: "Pérez",
      motivoQ: "higiene",
    };

    await fetchAllNotificacionesForExport({
      desde: "2020-01-01",
      hasta: "2020-01-31",
      plazoSlice: "total",
      historialAppliedPayload: payload,
    });

    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "notificacion",
      3,
      expect.objectContaining({
        omitirRangoFecha: true,
        calleQ: "Corrientes",
        contribuyenteQ: "Pérez",
        motivoQ: "higiene",
      })
    );
  });

  it("sin historialAppliedPayload usa período del diálogo", async () => {
    await fetchAllNotificacionesForExport({
      desde: "2026-03-01",
      hasta: "2026-03-31",
      plazoSlice: "total",
    });

    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      "2026-03-01",
      "2026-03-31",
      "notificacion",
      null,
      expect.any(Object)
    );
  });
});
