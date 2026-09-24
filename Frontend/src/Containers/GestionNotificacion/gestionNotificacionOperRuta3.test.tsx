import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  buildOperativaNotificacionFiltroPayload,
  operativaNotificacionTieneFiltro,
} from "./utils/buildOperativaNotificacionFiltroPayload";
import {
  isOperativeNotificacionTab,
  shouldResetOperativaFiltroOnTabChange,
} from "./utils/operativaNotificacionTabChange";
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
  it("U1 — payload sin OT, solo número y calle", () => {
    expect(
      buildOperativaNotificacionFiltroPayload({
        desde: " 2026-04-01 ",
        hasta: "2026-04-30",
        numeroNotificacion: " 8091 ",
        calleQ: " san martin ",
      })
    ).toEqual({
      desde: "2026-04-01",
      hasta: "2026-04-30",
      numeroNotificacion: "8091",
      calleQ: "san martin",
    });
    expect(
      buildOperativaNotificacionFiltroPayload({
        desde: null,
        hasta: null,
        numeroNotificacion: "",
        calleQ: "",
      })
    ).not.toHaveProperty("ordenTrabajo");
  });

  it("detecta si hay filtros activos", () => {
    expect(
      operativaNotificacionTieneFiltro({
        desde: null,
        hasta: null,
        numeroNotificacion: null,
        calleQ: null,
      })
    ).toBe(false);
    expect(
      operativaNotificacionTieneFiltro({
        desde: null,
        hasta: null,
        numeroNotificacion: "123",
        calleQ: null,
      })
    ).toBe(true);
  });
});

describe("operativaNotificacionTabChange", () => {
  it("U5/U6 — reset al cambiar entre tabs operativos", () => {
    expect(shouldResetOperativaFiltroOnTabChange("en_plazo", "por_vencer")).toBe(true);
    expect(shouldResetOperativaFiltroOnTabChange("por_vencer", "vencidas_o_hoy")).toBe(true);
    expect(shouldResetOperativaFiltroOnTabChange("en_plazo", "en_plazo")).toBe(false);
    expect(shouldResetOperativaFiltroOnTabChange("en_plazo", "total")).toBe(false);
    expect(isOperativeNotificacionTab("total")).toBe(false);
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
    vi.clearAllMocks();
    vi.mocked(getActuacionesPendientesExpediente).mockResolvedValue({
      items: [],
      meta: { total: 0, desde: null, hasta: null, source_type: "notificacion" },
    });
    vi.mocked(getPendientesReinspeccionNotificacion).mockResolvedValue([]);
  });

  it("U2 — en plazo envía solo plazo_slice=en_plazo con número", async () => {
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "en_plazo",
      numeroNotificacion: "123",
    });
    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "notificacion",
      null,
      expect.objectContaining({ plazoSlice: "en_plazo", numeroNotificacion: "123" })
    );
    expect(getPendientesReinspeccionNotificacion).not.toHaveBeenCalled();
  });

  it("U3 — por vencer envía solo plazo_slice=por_vencer", async () => {
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "por_vencer",
      numeroNotificacion: "456",
    });
    expect(getActuacionesPendientesExpediente).toHaveBeenCalledWith(
      undefined,
      undefined,
      "notificacion",
      null,
      expect.objectContaining({ plazoSlice: "por_vencer", numeroNotificacion: "456" })
    );
  });

  it("U4 — reinspección solo pendientes-notificacion", async () => {
    await getPendientesReinspeccionNotificacion({
      numeroNotificacion: "456",
      calleQ: "mitre",
    });
    expect(getPendientesReinspeccionNotificacion).toHaveBeenCalledWith({
      numeroNotificacion: "456",
      calleQ: "mitre",
    });
    expect(getActuacionesPendientesExpediente).not.toHaveBeenCalled();
  });

  it("en plazo envía calle sin OT", async () => {
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "en_plazo",
      calleQ: "san martin",
    });
    const opts = vi.mocked(getActuacionesPendientesExpediente).mock.calls.at(-1)?.[4];
    expect(opts).toMatchObject({ calleQ: "san martin", plazoSlice: "en_plazo" });
    expect(opts).not.toHaveProperty("ordenTrabajo");
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
