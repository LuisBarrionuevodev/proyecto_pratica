import { describe, expect, it } from "vitest";

import { COLUMN_DEFINITIONS } from "./columnDefinitions";
import { createGridTheme } from "../../CargarActuaciones/config/gridTheme";
import { darkColors, lightColors } from "../../../theme/colors";
import { glideColumnHeaderThemeOverride } from "../../CargarActuaciones/config/glideGridSemantics";

describe("FRONT-PROD.3.1 — Glide relevamientos columnas", () => {
  it("cada columna tiene title no vacío", () => {
    expect(COLUMN_DEFINITIONS.length).toBeGreaterThan(0);
    for (const col of COLUMN_DEFINITIONS) {
      expect(col.title?.trim()).not.toBe("");
      expect(col.id?.trim()).not.toBe("");
    }
  });

  it("header theme contrasta texto y fondo en dark y light", () => {
    const darkHeader = glideColumnHeaderThemeOverride(darkColors);
    const lightHeader = glideColumnHeaderThemeOverride(lightColors);
    expect(darkHeader.textHeader).toBe(darkColors.text.primary);
    expect(lightHeader.textHeader).toBe(lightColors.text.primary);
    expect(darkHeader.bgHeader).not.toBe(darkHeader.textHeader);
    expect(lightHeader.bgHeader).not.toBe(lightHeader.textHeader);
  });

  it("createGridTheme light usa header elevated y texto primary", () => {
    const theme = createGridTheme(lightColors);
    expect(theme.textHeader).toBe(lightColors.text.primary);
    expect(theme.bgHeader).toBe(lightColors.surface.panelElevated);
  });
});
