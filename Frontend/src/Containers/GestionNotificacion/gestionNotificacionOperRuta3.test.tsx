import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  buildOperativaNotificacionFiltroPayload,
  operativaNotificacionTieneFiltro,
} from "./utils/buildOperativaNotificacionFiltroPayload";
import {
  notificacionEstadoOperativoChipColor,
  notificacionEstadoOperativoLabel,
} from "./utils/notificacionEstadoOperativo";
import { getActuacionesPendientesExpediente, getPendientesReinspeccionNotificacion } from "../../api/actuacionesPendientesApi";

vi.mock("../../api/actuacionesPendientesApi", () => ({
  getActuacionesPendientesExpediente: vi.fn(),
  getPendientesReinspeccionNotificacion: vi.fn(),
  postSyncNotificacionesVencidas: vi.fn(),
  createExpedienteDesdeActuacion: vi.fn(),
}));

describe("buildOperativaNotificacionFiltroPayload", () => {
  it("normaliza desde/hasta y número", () => {
    expect(
      buildOperativaNotificacionFiltroPayload({
        desde: " 2026-04-01 ",
        hasta: "2026-04-30",
        numeroNotificacion: " 8091 ",
      })
    ).toEqual({
      desde: "2026-04-01",
      hasta: "2026-04-30",
      numeroNotificacion: "8091",
    });
  });

  it("detecta si hay filtros activos", () => {
    expect(
      operativaNotificacionTieneFiltro({
        desde: null,
        hasta: null,
        numeroNotificacion: null,
      })
    ).toBe(false);
    expect(
      operativaNotificacionTieneFiltro({
        desde: "2026-04-01",
        hasta: null,
        numeroNotificacion: null,
      })
    ).toBe(true);
  });
});

describe("notificacionEstadoOperativo", () => {
  it("traduce estados esperados", () => {
    expect(notificacionEstadoOperativoLabel("pendiente")).toBe("Pendiente");
    expect(notificacionEstadoOperativoLabel("en_pool")).toBe("En pool");
    expect(notificacionEstadoOperativoLabel("en_ruta_borrador")).toBe("En ruta borrador");
    expect(notificacionEstadoOperativoLabel("en_ruta_publicada")).toBe("En ruta publicada");
    expect(notificacionEstadoOperativoLabel("resuelto")).toBe("Resuelto");
    expect(notificacionEstadoOperativoLabel("no_elegible")).toBe("No elegible");
  });

  it("asigna color de chip por estado", () => {
    expect(notificacionEstadoOperativoChipColor("pendiente")).toBe("info");
    expect(notificacionEstadoOperativoChipColor("en_pool")).toBe("warning");
    expect(notificacionEstadoOperativoChipColor("en_ruta_publicada")).toBe("error");
  });
});

describe("API operativa notificaciones", () => {
  beforeEach(() => {
    vi.mocked(getActuacionesPendientesExpediente).mockResolvedValue({
      items: [],
      meta: { total: 0, desde: null, hasta: null, source_type: "notificacion" },
    });
    vi.mocked(getPendientesReinspeccionNotificacion).mockResolvedValue([]);
  });

  it("en plazo envía desde/hasta sin omitir_rango_fecha cuando hay rango", async () => {
    await getActuacionesPendientesExpediente("2026-04-01", "2026-04-30", "notificacion", null, {
      plazoSlice: "en_plazo",
      numeroNotificacion: "123",
    });
    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      "2026-04-01",
      "2026-04-30",
      "notificacion",
      null,
      expect.objectContaining({
        plazoSlice: "en_plazo",
        numeroNotificacion: "123",
      })
    );
    const opts = vi.mocked(getActuacionesPendientesExpediente).mock.calls[0][4];
    expect(opts?.omitirRangoFecha).toBeUndefined();
  });

  it("en plazo mantiene omitir_rango_fecha sin fechas", async () => {
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "en_plazo",
    });
    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "notificacion",
      null,
      expect.objectContaining({ omitirRangoFecha: true, plazoSlice: "en_plazo" })
    );
  });

  it("pendiente reinspección envía filtros al backend", async () => {
    await getPendientesReinspeccionNotificacion({
      desde: "2026-05-01",
      hasta: "2026-05-31",
      numeroNotificacion: "456",
    });
    expect(getPendientesReinspeccionNotificacion).toHaveBeenCalledWith({
      desde: "2026-05-01",
      hasta: "2026-05-31",
      numeroNotificacion: "456",
    });
  });
});

describe("GestionNotificacion chips (unit)", () => {
  it("expone label En pool para chip read-only", () => {
    expect(notificacionEstadoOperativoLabel("en_pool")).toBe("En pool");
    expect(notificacionEstadoOperativoChipColor("en_pool")).toBe("warning");
  });

  it("expone label En ruta publicada", () => {
    expect(notificacionEstadoOperativoLabel("en_ruta_publicada")).toBe("En ruta publicada");
  });
});
