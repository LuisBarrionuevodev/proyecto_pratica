import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { darkColors, lightColors } from "./colors";
import { resolveGlideCellTheme } from "../Containers/CargarActuaciones/config/glideGridSemantics";
import { createGridTheme } from "../Containers/CargarActuaciones/config/gridTheme";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

describe("THEME-FINAL.1 — modales y Glide", () => {
  it("dark modal surfaces — jerarquía profunda", () => {
    expect(darkColors.surface.panelElevated).toBe("#1C2028");
    expect(darkColors.surface.dialogTitle).toBe("#252A33");
    expect(darkColors.surface.dialogContent).toBe("#1E222A");
    expect(darkColors.surface.panelSubtle).toBe("#292E38");
    expect(darkColors.surface.input).toBe("#15191F");
    expect(darkColors.surface.dialogActions).toBe("#171B22");
    expect(darkColors.text.primary).toBe("#FFFFFF");
    expect(darkColors.text.secondary).toBe("rgba(255, 255, 255, 0.76)");
    expect(darkColors.border.default).toBe("rgba(255, 255, 255, 0.10)");
  });

  it("Glide painted cells — text.primary en dark y light", () => {
    for (const state of ["error", "ok", "pending"] as const) {
      expect(resolveGlideCellTheme(darkColors, state).textDark).toBe("#FFFFFF");
      expect(resolveGlideCellTheme(lightColors, state).textDark).toBe("#18202C");
      expect(resolveGlideCellTheme(darkColors, state).baseFontStyle).toBe("700 13px");
    }
  });

  it("Glide grid base/header font 13px", () => {
    expect(createGridTheme(darkColors).baseFontStyle).toBe("13px");
    expect(createGridTheme(lightColors).headerFontStyle).toBe("700 13px");
  });

  it("AppDialog close glass normal usa tokens semánticos", () => {
    const appDialog = readSrc("ui/AppDialog.tsx");
    expect(appDialog).toContain("GLASS_COLORS.textSecondary");
    expect(appDialog).toContain("closeButtonOnPrimary");
    expect(appDialog).toMatch(/closeButtonOnPrimary[\s\S]*rgba\(255,255,255/);
  });

  it("Completar trabajo modal sin texto UI blanco hardcodeado", () => {
    const modal = readSrc("Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx");
    expect(modal).toContain("GLASS_COLORS.textPrimary");
    expect(modal).not.toMatch(/color:\s*"rgba\(255,255,255/);
  });

  it("CrudGlassDialog no fuerza X sobre header primario", () => {
    const crud = readSrc("components/crudDialog/CrudGlassDialog.tsx");
    expect(crud).not.toContain("closeButtonOnPrimary");
  });
});
