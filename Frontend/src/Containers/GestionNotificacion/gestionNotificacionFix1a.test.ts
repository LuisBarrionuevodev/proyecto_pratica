import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("GESTIÓN-FIX.1A Notificación", () => {
  const page = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");

  it("usa persistKey scoped por actuacionId + op", () => {
    expect(page).toContain("persistKey");
    expect(page).toContain("GESTION_PERSIST_OPS.notifAltaExpediente");
    expect(page).toContain("modalAltaExpedientePersisting");
    expect(page).toContain("isPersistingForRow");
  });

  it("openModal invalida mutaciones previas y limpia persistKey", () => {
    expect(page).toMatch(/openModal[\s\S]*invalidatePendingMutationCallbacks/);
    expect(page).toMatch(/openModal[\s\S]*setPersistKey\(null\)/);
  });

  it("handleSave no await refresh de bandejas en camino crítico", () => {
    const saveBlock = page.slice(page.indexOf("const handleSave"), page.indexOf("const columnsDataCompact"));
    expect(saveBlock).not.toMatch(/await refreshBandejaActiva/);
    expect(saveBlock).not.toMatch(/await refreshNotificacionesPostProrroga/);
    expect(saveBlock).toContain("reconcileBandejasSilent");
    expect(saveBlock).toContain("nextMutationSeq");
    expect(saveBlock).toContain("isMutationSeqCurrent");
  });

  it("libera persistKey y cierra modal antes de reconciliación", () => {
    const saveBlock = page.slice(page.indexOf("const handleSave"), page.indexOf("const columnsDataCompact"));
    const clearIdx = saveBlock.indexOf("clearPersistKeyIfMatch");
    const dismissIdx = saveBlock.indexOf("dismissModal()");
    const reconcileIdx = saveBlock.indexOf("reconcileBandejasSilent");
    expect(clearIdx).toBeGreaterThan(-1);
    expect(dismissIdx).toBeGreaterThan(clearIdx);
    expect(reconcileIdx).toBeGreaterThan(dismissIdx);
  });

  it("reconciliación en background con todos los loads silent", () => {
    expect(page).toContain("runGestionReconcile");
    expect(page).toContain("GESTION_RECONCILE_REFRESH_MSG");
    expect(page).toMatch(/reconcileBandejasSilent[\s\S]*silent: true/);
  });

  it("mutación inline usa reconcile sin await en handler padre", () => {
    const block = page.slice(
      page.indexOf("handleExpedienteMutacionExitosa"),
      page.indexOf("const handleSave")
    );
    expect(block).not.toContain("await refresh");
    expect(block).toContain("reconcileBandejasSilent");
    expect(block).toContain("isMutationSeqCurrent");
  });

  it("modal recibe saving scoped al registro activo", () => {
    expect(page).toContain("saving={modalAltaExpedientePersisting}");
    expect(page).not.toContain("saving={saving}");
  });

  it("closeModal bloquea solo persistencia del alta expediente", () => {
    expect(page).toMatch(/closeModal[\s\S]*modalAltaExpedientePersisting/);
  });
});
