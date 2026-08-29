import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("GESTIÓN-FIX.1A Comprobación — expediente salida", () => {
  const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");

  it("usa dismissModalExp sin guard de saving en flujo exitoso", () => {
    const saveBlock = page.slice(page.indexOf("const handleSaveExpediente"), page.indexOf("const onReinBandejasActualizadas"));
    expect(saveBlock).toContain("dismissModalExp");
    expect(saveBlock).not.toMatch(/closeModalExp\(\)/);
  });

  it("dismissModalExp no comprueba savingExp", () => {
    const dismissBlock = page.slice(page.indexOf("const dismissModalExp"), page.indexOf("const modalExpPersisting"));
    expect(dismissBlock).not.toContain("savingExp");
    expect(dismissBlock).not.toContain("if (");
  });

  it("closeModalExp bloquea solo persistencia scoped", () => {
    expect(page).toMatch(/closeModalExp[\s\S]*modalExpPersisting/);
    expect(page).toContain("GESTION_PERSIST_OPS.compExpedienteSalida");
  });

  it("handleSaveExpediente no await refresh de bandejas", () => {
    const saveBlock = page.slice(page.indexOf("const handleSaveExpediente"), page.indexOf("const onReinBandejasActualizadas"));
    expect(saveBlock).not.toMatch(/await refreshActiveBandeja/);
    expect(saveBlock).not.toMatch(/await refreshComprobaciones/);
    expect(saveBlock).toContain("reconcileComprobacionesSilent");
  });

  it("libera persistKey y cierra antes de reconciliar", () => {
    const saveBlock = page.slice(page.indexOf("const handleSaveExpediente"), page.indexOf("const onReinBandejasActualizadas"));
    const clearIdx = saveBlock.indexOf("clearPersistKeyIfMatch");
    const dismissIdx = saveBlock.indexOf("dismissModalExp");
    const reconcileIdx = saveBlock.indexOf("reconcileComprobacionesSilent");
    expect(clearIdx).toBeGreaterThan(-1);
    expect(dismissIdx).toBeGreaterThan(clearIdx);
    expect(reconcileIdx).toBeGreaterThan(dismissIdx);
  });

  it("openModalExp invalida mutación previa", () => {
    expect(page).toMatch(/openModalExp[\s\S]*invalidatePendingMutationCallbacks/);
  });
});

describe("GESTIÓN-FIX.1A Comprobación — oficio", () => {
  const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
  const dialog = read("src/Containers/ActasComprobacion/components/ComprobacionOficioOperativoDialog.tsx");

  it("handleSaveOficio no await refresh en camino crítico", () => {
    const saveBlock = page.slice(page.indexOf("const handleSaveOficio"), page.indexOf("const columnsRein"));
    expect(saveBlock).not.toMatch(/await refreshModalOficioData/);
    expect(saveBlock).not.toMatch(/await refreshActiveBandeja/);
    expect(saveBlock).toContain("reconcileOficioPostAlta");
  });

  it("usa modalOficioPersisting scoped y documentalReconciling separado", () => {
    expect(page).toContain("modalOficioPersisting");
    expect(page).toContain("modalDocReconciling");
    expect(page).toContain("documentalReconciling={modalDocReconciling}");
    expect(page).toContain("saving={modalOficioPersisting}");
  });

  it("closeModalOficio bloquea solo persistencia scoped", () => {
    const closeBlock = page.slice(page.indexOf("const closeModalOficio"), page.indexOf("const dismissModalOficio"));
    expect(closeBlock).toContain("modalOficioPersisting");
    expect(closeBlock).not.toContain("modalDocReconciling");
  });

  it("dialog muestra actualizando información al reconciliar", () => {
    expect(dialog).toContain("documentalReconciling");
    expect(dialog).toContain("Actualizando información");
  });

  it("reconcileOficioPostAlta verifica seq y actuacionId", () => {
    expect(page).toMatch(/reconcileOficioPostAlta[\s\S]*isMutationSeqCurrent/);
    expect(page).toMatch(/reconcileOficioPostAlta[\s\S]*selectedOficioRef/);
  });
});
