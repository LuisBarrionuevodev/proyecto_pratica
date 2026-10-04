import { describe, expect, it } from "vitest";

import { darkColors, lightColors } from "../../../theme/colors";
import { resolveGlideCellTheme, resolveGlideDropdownCellTheme } from "./glideGridSemantics";

describe("glideGridSemantics", () => {
  it("resolveGlideCellTheme ok/error/pending — contraste painted", () => {
    for (const state of ["error", "ok", "pending"] as const) {
      const dark = resolveGlideCellTheme(darkColors, state);
      const light = resolveGlideCellTheme(lightColors, state);
      expect(dark.textDark).toBe("#FFFFFF");
      expect(light.textDark).toBe("#18202C");
      expect(dark.baseFontStyle).toBe("700 13px");
      expect(light.baseFontStyle).toBe("700 13px");
    }
  });

  it("resolveGlideDropdownCellTheme fuerza textMedium legible", () => {
    const dark = resolveGlideDropdownCellTheme(darkColors, "ok");
    expect(dark.textMedium).toBe(darkColors.text.primary);
    expect(dark.textBubble).toBe(darkColors.text.primary);
  });

  it("resolveGlideCellTheme ok surfaces", () => {
    const darkOk = resolveGlideCellTheme(darkColors, "ok");
    const lightOk = resolveGlideCellTheme(lightColors, "ok");
    expect(darkOk.bgCell).toBe(darkColors.status.successSurface);
    expect(lightOk.bgCell).toBe(lightColors.status.successSurface);
  });
});
