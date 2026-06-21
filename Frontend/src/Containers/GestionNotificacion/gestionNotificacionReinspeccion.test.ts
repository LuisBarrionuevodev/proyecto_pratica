import { describe, expect, it, vi } from "vitest";

import {
  countByPlazoSlice,
  matchesPlazoSlice,
  sliceLabel,
} from "./gestionNotificacionPlazo";
import { reinspeccionNotificacionBandejaRowKey } from "./gestionNotificacionReinspeccionRowKey";
import {
  emitGestionNotificacionReinspeccionRefresh,
  GESTION_NOTIF_REINSPECCION_REFRESH_EVENT,
  subscribeGestionNotificacionReinspeccionRefresh,
} from "./gestionNotificacionReinspeccionRefresh";
import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

function row(overrides: Partial<IActuacionesPendientesItem> = {}): IActuacionesPendientesItem {
  return {
    id: 1,
    source_type: "NOTIFICACION",
    dias_restantes: 0,
    ...overrides,
  } as IActuacionesPendientesItem;
}

describe("gestionNotificacionPlazo", () => {
  it("muestra label Pendiente reinspección para vencidas_o_hoy", () => {
    expect(sliceLabel("vencidas_o_hoy")).toBe("Pendiente reinspección");
  });

  it("no clasifica filas de plazo en vencidas_o_hoy", () => {
    expect(matchesPlazoSlice(row({ dias_restantes: 0 }), "vencidas_o_hoy")).toBe(false);
    expect(matchesPlazoSlice(row({ dias_restantes: 3 }), "por_vencer")).toBe(true);
  });

  it("cuenta pendiente reinspección desde parámetro separado", () => {
    const counts = countByPlazoSlice([row({ dias_restantes: 10 }), row({ dias_restantes: 2 })], 5);
    expect(counts.en_plazo).toBe(1);
    expect(counts.por_vencer).toBe(1);
    expect(counts.vencidas_o_hoy).toBe(5);
  });
});

describe("reinspeccionNotificacionBandejaRowKey", () => {
  it("prefiere iniciador_id", () => {
    expect(reinspeccionNotificacionBandejaRowKey(row({ id: 10, iniciador_id: 301 }))).toBe("301");
  });

  it("usa bandeja_row_key si viene del backend", () => {
    expect(
      reinspeccionNotificacionBandejaRowKey(row({ id: 10, iniciador_id: 301, bandeja_row_key: "10-301" }))
    ).toBe("10-301");
  });
});

describe("gestionNotificacionReinspeccionRefresh", () => {
  it("emite evento de refresh", () => {
    const listeners = new Map<string, Set<EventListener>>();
    const mockWindow = {
      addEventListener: (type: string, listener: EventListener) => {
        if (!listeners.has(type)) listeners.set(type, new Set());
        listeners.get(type)!.add(listener);
      },
      removeEventListener: (type: string, listener: EventListener) => {
        listeners.get(type)?.delete(listener);
      },
      dispatchEvent: (event: Event) => {
        listeners.get(event.type)?.forEach((listener) => listener(event));
        return true;
      },
    };
    vi.stubGlobal("window", mockWindow);

    const listener = vi.fn();
    const off = subscribeGestionNotificacionReinspeccionRefresh(listener);
    emitGestionNotificacionReinspeccionRefresh();
    expect(listener).toHaveBeenCalledTimes(1);
    off();
    emitGestionNotificacionReinspeccionRefresh();
    expect(listener).toHaveBeenCalledTimes(1);
    expect(GESTION_NOTIF_REINSPECCION_REFRESH_EVENT).toBe("gestion-notif:reinspeccion-refresh");

    vi.unstubAllGlobals();
  });
});

describe("getPendientesReinspeccionNotificacion API", () => {
  it("expone endpoint de cola operativa", async () => {
    const { getPendientesReinspeccionNotificacion } = await import("../../api/actuacionesPendientesApi");
    const apiClient = await import("../../api/apiClient");
    const getSpy = vi.spyOn(apiClient.apiClient, "get").mockResolvedValue({ data: [] });
    await getPendientesReinspeccionNotificacion();
    expect(getSpy).toHaveBeenCalledWith("/actuaciones/pendientes-notificacion");
    getSpy.mockRestore();
  });
});

describe("notificacionesExportApi reinspeccion slice", () => {
  it("usa pendientes-notificacion para vencidas_o_hoy", async () => {
    const pendientesApi = await import("../../api/actuacionesPendientesApi");
    const reinSpy = vi.spyOn(pendientesApi, "getPendientesReinspeccionNotificacion").mockResolvedValue([]);
    const expSpy = vi.spyOn(pendientesApi, "getActuacionesPendientesExpediente");
    const { fetchAllNotificacionesForExport } = await import("../../api/notificacionesExportApi");
    await fetchAllNotificacionesForExport({
      desde: "2026-01-01",
      hasta: "2026-01-31",
      plazoSlice: "vencidas_o_hoy",
    });
    expect(reinSpy).toHaveBeenCalled();
    expect(expSpy).not.toHaveBeenCalled();
    reinSpy.mockRestore();
    expSpy.mockRestore();
  });
});
