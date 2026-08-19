import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { refreshComprobacionesPostOficio } from "./utils/refreshComprobacionesPostOficio";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("UI-LOAD.1 Comprobaciones — loading único", () => {
  const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
  const oficioDialog = read("src/Containers/ActasComprobacion/components/ComprobacionOficioOperativoDialog.tsx");

  it("tabs pendientes usan BandejaTableSpinner sin overlay", () => {
    expect(page).toContain("BandejaTableSpinner");
    expect(page).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(page).not.toContain("opacity: expLoading");
    expect(page).not.toContain("opacity: oficioLoading");
    expect(page).not.toContain("opacity: reinLoading");
  });

  it("recorrido usa BandejaTableSpinner al filtrar", () => {
    expect(page).toMatch(/recLoading[\s\S]*BandejaTableSpinner/);
  });

  it("modal oficio muestra busy en guardar y eliminar", () => {
    expect(oficioDialog).toContain('saving ? "Guardando…"');
    expect(oficioDialog).toContain("loading={delBloqueSaving}");
    expect(oficioDialog).toContain("disabled={saving");
  });

  it("post oficio usa refreshComprobacionesPostOficio", () => {
    expect(page).toContain("refreshComprobacionesPostOficio");
    expect(page).toContain("refreshComprobacionesSlices");
  });
});

describe("refreshComprobacionesPostOficio", () => {
  it("refresca tres bandejas pendientes; activa sin silent", async () => {
    const invalidatePendientesTabs = vi.fn();
    const loadExpediente = vi.fn().mockResolvedValue(undefined);
    const loadOficio = vi.fn().mockResolvedValue(undefined);
    const loadRein = vi.fn().mockResolvedValue(undefined);

    await refreshComprobacionesPostOficio({
      filters: null,
      activeTab: "oficio",
      invalidatePendientesTabs,
      loadExpediente,
      loadOficio,
      loadRein,
    });

    expect(invalidatePendientesTabs).toHaveBeenCalledOnce();
    expect(loadOficio).toHaveBeenCalledWith(null, { silent: false });
    expect(loadExpediente).toHaveBeenCalledWith(null, { silent: true });
    expect(loadRein).toHaveBeenCalledWith(null, { silent: true });
  });
});
