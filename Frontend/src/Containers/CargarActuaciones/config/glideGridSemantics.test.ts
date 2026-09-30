import { describe, expect, it } from "vitest";

import { darkColors, lightColors } from "../../../theme/colors";
import { resolveGlideCellTheme } from "./glideGridSemantics";

describe("glideGridSemantics", () => {
  it("resolveGlideCellTheme ok/error difiere entre dark y light", () => {
    const darkOk = resolveGlideCellTheme(darkColors, "ok");
    const lightOk = resolveGlideCellTheme(lightColors, "ok");
    expect(darkOk.bgCell).toBe(darkColors.status.successSurface);
    expect(lightOk.bgCell).toBe(lightColors.status.successSurface);
    expect(darkOk.textDark).not.toBe(lightOk.textDark);
  });
});
