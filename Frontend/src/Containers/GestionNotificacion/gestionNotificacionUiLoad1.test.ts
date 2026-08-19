import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { refreshNotificacionesPostProrroga } from "./utils/refreshNotificacionesPostProrroga";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("UI-LOAD.1 Notificaciones — loading único", () => {
  const page = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
  const dialog = read("src/Containers/GestionNotificacion/components/NotificacionDetalleDocumentalDialog.tsx");

  it("operativa usa BandejaTableSpinner sin overlay MRT", () => {
    expect(page).toContain("BandejaTableSpinner");
    expect(page).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(page).not.toContain("showProgressBars: loading");
    expect(page).not.toContain("opacity: operativaLoading");
  });

  it("historial usa BandejaTableSpinner", () => {
    expect(page).toMatch(/historialLoading[\s\S]*BandejaTableSpinner/);
  });

  it("modal prórroga muestra Guardando y deshabilita campos", () => {
    expect(dialog).toContain('saving ? "Guardando…"');
    expect(dialog).toContain("disabled={saving}");
    expect(dialog).toContain("loading={delSaving}");
  });

  it("post prórroga usa refreshNotificacionesPostProrroga", () => {
    expect(page).toContain("refreshNotificacionesPostProrroga");
    expect(page).toContain("refreshNotificacionesSlices");
  });
});

describe("refreshNotificacionesPostProrroga", () => {
  it("refresca los tres slices; activo sin silent", async () => {
    const invalidateOperativeSlices = vi.fn();
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga({
      filters: null,
      activeSlice: "en_plazo",
      invalidateOperativeSlices,
      loadPlazoSlice,
      loadReinspeccion,
    });

    expect(invalidateOperativeSlices).toHaveBeenCalledOnce();
    expect(loadPlazoSlice).toHaveBeenCalledWith("en_plazo", true, null, { silent: false });
    expect(loadPlazoSlice).toHaveBeenCalledWith("por_vencer", true, null, { silent: true });
    expect(loadReinspeccion).toHaveBeenCalledWith(null, { silent: true });
  });

  it("pendiente reinspección activo refresca reinspeccion visible", async () => {
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga({
      filters: null,
      activeSlice: "vencidas_o_hoy",
      invalidateOperativeSlices: vi.fn(),
      loadPlazoSlice,
      loadReinspeccion,
    });

    expect(loadReinspeccion).toHaveBeenCalledWith(null, { silent: false });
    expect(loadPlazoSlice).toHaveBeenCalledWith("en_plazo", true, null, { silent: true });
  });
});
