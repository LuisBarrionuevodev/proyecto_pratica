import { describe, expect, it } from "vitest";

import { createAppTheme } from "../../configs/theme";
import { darkColors, getSemanticColors, lightColors, semanticColors } from "./index";
import { legacyGlassColorMap } from "./legacyGlass";
import { color as tokenColor } from "../tokens";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import { DATA_TABLE_MRT_GLASS_COLORS } from "../../styles/mrtGlassDataTablePreset";
import {
  DATA_TABLE_CONFIG,
  DARK_TABLE_CONFIG,
} from "../../Containers/Actuaciones/styles/actuacionesTableStyles";
import { CSS_VAR_NAMES } from "../applyCssVariables";

function semanticKeys(obj: Record<string, unknown>): string[] {
  return Object.keys(obj).sort();
}

describe("FRONT-PROD.2/3 — tokens semánticos", () => {
  it("dark y light comparten la misma estructura semántica", () => {
    expect(semanticKeys(darkColors)).toEqual(semanticKeys(lightColors));
    expect(semanticKeys(darkColors.surface)).toEqual(semanticKeys(lightColors.surface));
    expect(semanticKeys(darkColors.text)).toEqual(semanticKeys(lightColors.text));
    expect(semanticKeys(darkColors.action)).toEqual(semanticKeys(lightColors.action));
    expect(semanticKeys(darkColors.calendar)).toEqual(semanticKeys(lightColors.calendar));
    expect(semanticKeys(darkColors.chart)).toEqual(semanticKeys(lightColors.chart));
    expect(semanticKeys(darkColors.profile)).toEqual(semanticKeys(lightColors.profile));
  });

  it("getSemanticColors resuelve paletas sin mutar", () => {
    expect(getSemanticColors("dark")).toBe(darkColors);
    expect(getSemanticColors("light")).toBe(lightColors);
    expect(darkColors.action.primary).toBe("#0166FF");
    expect(lightColors.action.primary).toBe("#0166FF");
  });

  it("legacy GLASS_COLORS usa CSS variables dinámicas", () => {
    expect(legacyGlassColorMap.textPrimary).toContain("var(--d-text-primary)");
    expect(tokenColor.textPrimary).toBe(legacyGlassColorMap.textPrimary);
    expect(GLASS_COLORS.cardBg).toContain("var(--d-surface-panel)");
  });

  it("MRT preset usa variables CSS para filas y texto", () => {
    expect(DATA_TABLE_MRT_GLASS_COLORS.rowOdd).toBe(`var(${CSS_VAR_NAMES.tableRowOdd})`);
    expect(DATA_TABLE_MRT_GLASS_COLORS.white).toBe(`var(${CSS_VAR_NAMES.textPrimary})`);
  });

  it("DATA_TABLE_CONFIG es alias canónico de DARK_TABLE_CONFIG", () => {
    expect(DATA_TABLE_CONFIG).toBe(DARK_TABLE_CONFIG);
  });

  it("createAppTheme respeta modo y semántica", () => {
    const darkTheme = createAppTheme("dark");
    const lightTheme = createAppTheme("light");
    expect(darkTheme.palette.mode).toBe("dark");
    expect(lightTheme.palette.mode).toBe("light");
    expect(darkTheme.palette.text.primary).toBe(darkColors.text.primary);
    expect(lightTheme.palette.text.primary).toBe(lightColors.text.primary);
    expect(semanticColors).toBe(darkColors);
  });
});
