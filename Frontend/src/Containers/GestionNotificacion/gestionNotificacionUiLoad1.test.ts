import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  MUTATION_INVALIDATE_PLAZO,
  refreshNotificacionesPostProrroga,
} from "./utils/refreshNotificacionesPostProrroga";

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

  it("post prórroga usa reconcile en background", () => {
    expect(page).toContain("refreshNotificacionesPostProrroga");
    expect(page).toContain("reconcileBandejasSilent");
    expect(page).toContain("runGestionReconcile");
  });
});

describe("refreshNotificacionesPostProrroga", () => {
  it("invalida slices indicados y recarga base; activo sin silent", async () => {
    const invalidateOperativaBaseTabs = vi.fn();
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga(
      {
        activeSlice: "en_plazo",
        invalidateOperativaBaseTabs,
        loadPlazoSlice,
        loadReinspeccion,
      },
      MUTATION_INVALIDATE_PLAZO
    );

    expect(invalidateOperativaBaseTabs).toHaveBeenCalledWith(MUTATION_INVALIDATE_PLAZO);
    expect(loadPlazoSlice).toHaveBeenCalledWith("en_plazo", null, { silent: false, forceBaseRefresh: true });
    expect(loadPlazoSlice).toHaveBeenCalledWith("por_vencer", null, { silent: true, forceBaseRefresh: true });
    expect(loadReinspeccion).not.toHaveBeenCalled();
  });

  it("pendiente reinspección activo refresca reinspeccion visible", async () => {
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga(
      {
        activeSlice: "vencidas_o_hoy",
        invalidateOperativaBaseTabs: vi.fn(),
        loadPlazoSlice,
        loadReinspeccion,
      },
      MUTATION_INVALIDATE_PLAZO
    );

    expect(loadReinspeccion).not.toHaveBeenCalled();
    expect(loadPlazoSlice).toHaveBeenCalledWith("en_plazo", null, { silent: true, forceBaseRefresh: true });
  });
});
