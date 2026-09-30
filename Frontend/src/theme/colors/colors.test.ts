import { describe, expect, it } from "vitest";

import { appTheme } from "../../configs/theme";
import { darkColors, semanticColors } from "./index";
import { legacyGlassColorMap } from "./legacyGlass";
import { color as tokenColor } from "../tokens";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import { DATA_TABLE_MRT_GLASS_COLORS } from "../../styles/mrtGlassDataTablePreset";
import {
  DATA_TABLE_CONFIG,
  DARK_TABLE_CONFIG,
} from "../../Containers/Actuaciones/styles/actuacionesTableStyles";

describe("FRONT-PROD.2 — tokens semánticos dark", () => {
  it("darkColors define superficies, texto, borde, acción y status", () => {
    expect(darkColors.surface.panel).toMatch(/^rgba|#/);
    expect(darkColors.text.primary).toBeTruthy();
    expect(darkColors.border.subtle).toBeTruthy();
    expect(darkColors.action.primary).toBe("#0166FF");
    expect(darkColors.status.error).toBeTruthy();
    expect(semanticColors).toBe(darkColors);
  });

  it("legacy glass map y token.color coinciden con dark", () => {
    expect(legacyGlassColorMap.textPrimary).toBe(darkColors.text.primary);
    expect(tokenColor.primary).toBe(darkColors.action.primary);
    expect(GLASS_COLORS.cardBg).toBe(darkColors.surface.panel);
  });

  it("tablas MRT derivan primary y filas del mismo darkColors", () => {
    expect(DATA_TABLE_MRT_GLASS_COLORS.primary).toBe(darkColors.action.primary);
    expect(DATA_TABLE_MRT_GLASS_COLORS.rowOdd).toBe(darkColors.surface.tableRowOdd);
  });

  it("DATA_TABLE_CONFIG es alias canónico de DARK_TABLE_CONFIG", () => {
    expect(DATA_TABLE_CONFIG).toBe(DARK_TABLE_CONFIG);
  });

  it("appTheme permanece dark y palette alimentada por semántica", () => {
    expect(appTheme.palette.mode).toBe("dark");
    expect(appTheme.palette.primary.main).toBe(darkColors.action.primary);
    expect(appTheme.palette.background.default).toBe(darkColors.surface.app);
    expect(appTheme.palette.background.paper).toBe(darkColors.surface.panel);
    expect(appTheme.palette.text.primary).toBe(darkColors.text.primary);
    expect(appTheme.palette.text.secondary).toBe(darkColors.text.secondary);
    expect(appTheme.palette.divider).toBe(darkColors.border.subtle);
    expect(appTheme.palette.success?.main).toBe(darkColors.status.success);
    expect(appTheme.palette.error?.main).toBe(darkColors.status.error);
  });
});
