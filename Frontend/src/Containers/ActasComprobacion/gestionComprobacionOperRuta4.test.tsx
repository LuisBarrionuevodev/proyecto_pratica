import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  buildOperativaComprobacionFiltroPayload,
  operativaComprobacionTieneFiltro,
} from "./utils/buildOperativaComprobacionFiltroPayload";
import {
  notificacionEstadoOperativoChipColor,
  notificacionEstadoOperativoLabel,
} from "../GestionNotificacion/utils/notificacionEstadoOperativo";
import { getActuacionesPendientesExpediente } from "../../api/actuacionesPendientesApi";
import {
  fetchComprobacionPendientesOficio,
  fetchPendientesReinspeccionOficio,
} from "../../api/actuacionesComprobacionActasApi";

vi.mock("../../api/actuacionesPendientesApi", () => ({
  getActuacionesPendientesExpediente: vi.fn(),
  createExpedienteDesdeActuacion: vi.fn(),
  createOficioDesdeActuacion: vi.fn(),
  getJuzgadosCatalogoCached: vi.fn(),
}));

vi.mock("../../api/actuacionesComprobacionActasApi", () => ({
  fetchComprobacionPendientesOficio: vi.fn(),
  fetchPendientesReinspeccionOficio: vi.fn(),
  fetchComprobacionDocumental: vi.fn(),
  fetchOficiosByComprobacion: vi.fn(),
  fetchComprobacionRecorridoDetalle: vi.fn(),
}));

describe("buildOperativaComprobacionFiltroPayload", () => {
  it("normaliza desde/hasta y número de comprobación", () => {
    expect(
      buildOperativaComprobacionFiltroPayload({
        desde: " 2026-04-01 ",
        hasta: "2026-04-30",
        numeroComprobacion: " 8091 ",
      })
    ).toEqual({
      desde: "2026-04-01",
      hasta: "2026-04-30",
      numeroComprobacion: "8091",
    });
  });

  it("detecta si hay filtros activos", () => {
    expect(
      operativaComprobacionTieneFiltro({
        desde: null,
        hasta: null,
        numeroComprobacion: null,
      })
    ).toBe(false);
    expect(
      operativaComprobacionTieneFiltro({
        desde: "2026-04-01",
        hasta: null,
        numeroComprobacion: null,
      })
    ).toBe(true);
  });
});

describe("estado operativo comprobación (chips read-only)", () => {
  it("traduce No elegible y Pendiente", () => {
    expect(notificacionEstadoOperativoLabel("no_elegible")).toBe("No elegible");
    expect(notificacionEstadoOperativoLabel("pendiente")).toBe("Pendiente");
  });

  it("traduce En pool y En ruta", () => {
    expect(notificacionEstadoOperativoLabel("en_pool")).toBe("En pool");
    expect(notificacionEstadoOperativoLabel("en_ruta_borrador")).toBe("En ruta borrador");
    expect(notificacionEstadoOperativoLabel("en_ruta_publicada")).toBe("En ruta publicada");
  });

  it("asigna color de chip por estado", () => {
    expect(notificacionEstadoOperativoChipColor("no_elegible")).toBe("default");
    expect(notificacionEstadoOperativoChipColor("pendiente")).toBe("info");
    expect(notificacionEstadoOperativoChipColor("en_pool")).toBe("warning");
    expect(notificacionEstadoOperativoChipColor("en_ruta_publicada")).toBe("error");
  });
});

describe("API operativa comprobaciones", () => {
  beforeEach(() => {
    vi.mocked(getActuacionesPendientesExpediente).mockResolvedValue({
      items: [],
      meta: { total: 0, desde: null, hasta: null, source_type: "comprobacion" },
    });
    vi.mocked(fetchComprobacionPendientesOficio).mockResolvedValue({
      items: [],
      meta: { total: 0, desde: null, hasta: null },
    });
    vi.mocked(fetchPendientesReinspeccionOficio).mockResolvedValue({
      items: [],
      meta: { total: 0, desde: null, hasta: null },
    });
  });

  it("expediente envía desde/hasta sin omitir_rango_fecha cuando hay rango", async () => {
    await getActuacionesPendientesExpediente("2026-04-01", "2026-04-30", "comprobacion", null, {
      numeroComprobacion: "123",
    });
    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      "2026-04-01",
      "2026-04-30",
      "comprobacion",
      null,
      expect.objectContaining({ numeroComprobacion: "123" })
    );
    const opts = vi.mocked(getActuacionesPendientesExpediente).mock.calls[0][4];
    expect(opts?.omitirRangoFecha).toBeUndefined();
  });

  it("expediente mantiene omitir_rango_fecha sin fechas", async () => {
    await getActuacionesPendientesExpediente(undefined, undefined, "comprobacion", null, {
      omitirRangoFecha: true,
    });
    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "comprobacion",
      null,
      expect.objectContaining({ omitirRangoFecha: true })
    );
  });

  it("oficio envía numero_comprobacion al backend", async () => {
    await fetchComprobacionPendientesOficio(null, null, null, {
      omitirRangoFecha: true,
      numeroComprobacion: "456",
    });
    expect(fetchComprobacionPendientesOficio).toHaveBeenCalledWith(null, null, null, {
      omitirRangoFecha: true,
      numeroComprobacion: "456",
    });
  });

  it("reinspección envía filtros al backend", async () => {
    await fetchPendientesReinspeccionOficio("2026-05-01", "2026-05-31", null, {
      numeroComprobacion: "789",
    });
    expect(fetchPendientesReinspeccionOficio).toHaveBeenCalledWith("2026-05-01", "2026-05-31", null, {
      numeroComprobacion: "789",
    });
  });
});

describe("ActasComprobacion — sin acción Agregar al pool", () => {
  it("no define helper de agregar al pool en filtros operativos", () => {
    expect(typeof buildOperativaComprobacionFiltroPayload).toBe("function");
    expect(buildOperativaComprobacionFiltroPayload({ desde: null, hasta: null, numeroComprobacion: "" })).not.toHaveProperty(
      "agregarAlPool"
    );
  });
});
