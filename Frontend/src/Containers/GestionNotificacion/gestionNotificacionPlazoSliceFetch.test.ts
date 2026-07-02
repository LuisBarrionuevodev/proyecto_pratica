import { describe, expect, it, vi } from "vitest";

import {
  operativePlazoSlicePeerToInvalidate,
  operativePlazoSliceShouldFetch,
} from "./gestionNotificacionPlazo";

describe("getActuacionesPendientesExpediente plazo_slice", () => {
  it("envía plazo_slice=en_plazo para bandeja En plazo", async () => {
    const { getActuacionesPendientesExpediente } = await import("../../api/actuacionesPendientesApi");
    const apiClient = await import("../../api/apiClient");
    const getSpy = vi.spyOn(apiClient.apiClient, "get").mockResolvedValue({
      data: { items: [], meta: { total: 0, source_type: "notificacion" } },
    });
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "en_plazo",
    });
    expect(getSpy).toHaveBeenCalledWith("/actuaciones/pendientes/expediente", {
      params: expect.objectContaining({ plazo_slice: "en_plazo", omitir_rango_fecha: "true" }),
    });
    getSpy.mockRestore();
  });

  it("envía plazo_slice=por_vencer para bandeja Por vencer", async () => {
    const { getActuacionesPendientesExpediente } = await import("../../api/actuacionesPendientesApi");
    const apiClient = await import("../../api/apiClient");
    const getSpy = vi.spyOn(apiClient.apiClient, "get").mockResolvedValue({
      data: { items: [], meta: { total: 0, source_type: "notificacion" } },
    });
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "por_vencer",
    });
    expect(getSpy).toHaveBeenCalledWith("/actuaciones/pendientes/expediente", {
      params: expect.objectContaining({ plazo_slice: "por_vencer" }),
    });
    getSpy.mockRestore();
  });

  it("no envía plazo_slice para historial total", async () => {
    const { getActuacionesPendientesExpediente } = await import("../../api/actuacionesPendientesApi");
    const apiClient = await import("../../api/apiClient");
    const getSpy = vi.spyOn(apiClient.apiClient, "get").mockResolvedValue({
      data: { items: [], meta: { total: 0, source_type: "notificacion" } },
    });
    await getActuacionesPendientesExpediente("2026-01-01", "2026-01-31", "notificacion", null);
    expect(getSpy).toHaveBeenCalledWith("/actuaciones/pendientes/expediente", {
      params: expect.not.objectContaining({ plazo_slice: expect.anything() }),
    });
    getSpy.mockRestore();
  });

  it("acepta plazo_slice=total explícito sin romper la llamada", async () => {
    const { getActuacionesPendientesExpediente } = await import("../../api/actuacionesPendientesApi");
    const apiClient = await import("../../api/apiClient");
    const getSpy = vi.spyOn(apiClient.apiClient, "get").mockResolvedValue({
      data: { items: [], meta: { total: 0, source_type: "notificacion" } },
    });
    await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
      omitirRangoFecha: true,
      plazoSlice: "total",
    });
    expect(getSpy).toHaveBeenCalledWith("/actuaciones/pendientes/expediente", {
      params: expect.objectContaining({ plazo_slice: "total" }),
    });
    getSpy.mockRestore();
  });
});

describe("operative plazo slice cache", () => {
  it("no refetch si el slice ya está cargado", () => {
    const loaded = { en_plazo: true, por_vencer: false };
    expect(operativePlazoSliceShouldFetch("en_plazo", loaded)).toBe(false);
    expect(operativePlazoSliceShouldFetch("por_vencer", loaded)).toBe(true);
  });

  it("force refresh ignora cache del slice activo", () => {
    const loaded = { en_plazo: true, por_vencer: true };
    expect(operativePlazoSliceShouldFetch("por_vencer", loaded, true)).toBe(true);
  });

  it("post-modal invalida el slice complementario sin cargarlo", () => {
    expect(operativePlazoSlicePeerToInvalidate("en_plazo")).toBe("por_vencer");
    expect(operativePlazoSlicePeerToInvalidate("por_vencer")).toBe("en_plazo");
    const loaded = { en_plazo: true, por_vencer: true };
    loaded[operativePlazoSlicePeerToInvalidate("por_vencer")] = false;
    expect(loaded.en_plazo).toBe(false);
    expect(loaded.por_vencer).toBe(true);
  });
});

describe("notificacionesExportApi plazo_slice", () => {
  it("pasa plazo_slice al exportar En plazo", async () => {
    const pendientesApi = await import("../../api/actuacionesPendientesApi");
    const expSpy = vi.spyOn(pendientesApi, "getActuacionesPendientesExpediente").mockResolvedValue({
      items: [],
      meta: { total: 0, source_type: "notificacion", desde: null, hasta: null },
    });
    const { fetchAllNotificacionesForExport } = await import("../../api/notificacionesExportApi");
    await fetchAllNotificacionesForExport({
      desde: "2026-01-01",
      hasta: "2026-01-31",
      plazoSlice: "en_plazo",
    });
    expect(expSpy).toHaveBeenCalledWith(
      "2026-01-01",
      "2026-01-31",
      "notificacion",
      null,
      expect.objectContaining({ plazoSlice: "en_plazo" })
    );
    expSpy.mockRestore();
  });

  it("pendiente reinspección sigue usando pendientes-notificacion", async () => {
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
