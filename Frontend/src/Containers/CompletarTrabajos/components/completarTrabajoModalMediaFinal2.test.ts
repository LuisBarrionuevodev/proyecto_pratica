import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const modalSrc = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "CompletarTrabajoModal.tsx"),
  "utf8"
);

describe("MEDIA-FINAL.2 CompletarTrabajoModal", () => {
  it("CONTINUAR SUBIDA usa isCompletarTrabajoSoloFotosMode en handleSubmit", () => {
    expect(modalSrc).toMatch(
      /if\s*\(\s*isCompletarTrabajoSoloFotosMode\s*\(\s*uiPolicy\s*,\s*resolvedRow\s*\)\s*\)\s*\{/
    );
  });

  it("submitCierreOperativo no llama /cerrar en modo solo fotos", () => {
    expect(modalSrc).toMatch(
      /submitCierreOperativo[\s\S]{0,400}isCompletarTrabajoSoloFotosMode\s*\(\s*uiPolicy\s*,\s*resolvedRow\s*\)/
    );
    expect(modalSrc).toMatch(/isCompletarTrabajoCierreNoEnProcesoError/);
  });

  it("soloEvidenciasUi deriva de isCompletarTrabajoSoloFotosMode (no solo ui_policy aislado)", () => {
    expect(modalSrc).toContain(
      "const soloEvidenciasUi = isCompletarTrabajoSoloFotosMode(uiPolicy, resolvedRow);"
    );
    expect(modalSrc).not.toMatch(
      /const soloEvidenciasUi = uiPolicy\?\.solo_evidencias_pendientes === true/
    );
  });
});
