import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { createAppTheme } from "../configs/theme";
import { catalogDropdownPaperStyle } from "./catalogMenuTheme";
import { darkColors, lightColors } from "./colors";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

describe("HOTFIX V1.1-UX.1", () => {
  it("Completar trabajo activa fullscreen móvil en CrudGlassDialog", () => {
    const modal = readSrc("Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx");
    expect(modal).toContain("mobileFullScreen");
    expect(modal).toContain("CrudGlassDialog");
  });

  it("layout fullscreen usa 100dvh y scroll interno", () => {
    const patterns = readSrc("styles/responsivePatterns.ts");
    expect(patterns).toContain("100dvh");
    expect(patterns).toContain("responsiveDialogFullscreenContentLayoutSx");
    const appDialog = readSrc("ui/AppDialog.tsx");
    expect(appDialog).toContain("responsiveDialogFullscreenContentLayoutSx");
    const crudDialog = readSrc("components/crudDialog/CrudGlassDialog.tsx");
    expect(crudDialog).toMatch(/overflowY:\s*"auto"/);
    const crudTokens = readSrc("styles/crudDialogTokens.ts");
    expect(crudTokens).toContain("fontSize: \"16px\"");
  });

  it("tema MUI: catálogos sólidos sin backdrop-filter", () => {
    const lightPaper = catalogDropdownPaperStyle(lightColors, "light");
    const darkPaper = catalogDropdownPaperStyle(darkColors, "dark");
    expect(lightPaper.backdropFilter).toBe("none");
    expect(darkPaper.backdropFilter).toBe("none");
    expect(lightPaper.backgroundColor).toBe(lightColors.surface.tableRowEven);
    expect(darkPaper.backgroundColor).toBe(darkColors.surface.panel);

    const lightTheme = createAppTheme("light");
    const menuPaper = lightTheme.components?.MuiMenu?.styleOverrides?.paper as Record<string, unknown>;
    expect(menuPaper?.backgroundColor).toBe(lightColors.surface.tableRowEven);
    expect(menuPaper?.backdropFilter).toBe("none");

    const mobileInput = createAppTheme("dark").components?.MuiInputBase?.styleOverrides?.input as Record<
      string,
      unknown
    >;
    expect(mobileInput?.["@media (max-width: 599.95px)"]).toEqual({ fontSize: "16px" });
  });

  it("modal CRUD conserva glass en paper", () => {
    const crud = readSrc("styles/crudDialogTokens.ts");
    expect(crud).toContain("backdropFilter");
    expect(crud).toContain("blur(14px)");
  });
});
