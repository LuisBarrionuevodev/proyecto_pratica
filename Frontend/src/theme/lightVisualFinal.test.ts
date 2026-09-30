import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { CSS_VAR_NAMES } from "./applyCssVariables";
import { darkColors, lightColors } from "./colors";
import { createGridTheme } from "../Containers/CargarActuaciones/config/gridTheme";
import { glassContent, glassSidebar, glassTabsSecondaryPanelSx } from "../styles/GlassStyles";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

function rgbaAlpha(value: string): number | null {
  const m = value.match(/rgba?\([^)]+\)/);
  if (!m) return value.startsWith("#") ? 1 : null;
  const parts = m[0].replace(/rgba?\(|\)/g, "").split(",").map((p) => p.trim());
  if (parts.length === 4) return parseFloat(parts[3]);
  if (parts.length === 3) return 1;
  return null;
}

describe("LIGHT-VISUAL-FINAL — tokens y jerarquía", () => {
  it("lightColors calibración mockup", () => {
    expect(lightColors.text.primary).toBe("#18202C");
    expect(lightColors.text.secondary).toBe("#465160");
    expect(lightColors.action.primary).toBe("#0166FF");
    expect(lightColors.surface.tableHeader).toBe("#F6F8FB");
    expect(lightColors.surface.tableRowEven).toBe("#FFFFFF");
    expect(lightColors.action.tabSelected).toBe("#DDE9FA");
  });

  it("jerarquía shell < panel < elevated < input", () => {
    const shell = Math.max(
      rgbaAlpha(lightColors.surface.sidebar)!,
      rgbaAlpha(lightColors.surface.content)!
    );
    const panel = rgbaAlpha(lightColors.surface.panel)!;
    const elevated = rgbaAlpha(lightColors.surface.panelElevated)!;
    const input = rgbaAlpha(lightColors.surface.input)!;
    expect(shell).toBeLessThanOrEqual(0.65);
    expect(shell).toBeLessThan(panel);
    expect(panel).toBeLessThan(elevated);
    expect(elevated).toBeLessThan(input);
  });

  it("dark conserva tableHeader alineado a elevado", () => {
    expect(darkColors.surface.tableHeader).toBe(darkColors.surface.tableRowEven);
  });

  it("background light autenticado sin overlay", () => {
    const css = readSrc("index.css");
    const block = css.match(
      /\[data-theme="light"\] body\.authenticated-route\s*\{[\s\S]*?\}/
    )?.[0];
    expect(block).toContain("BackgroundInicioLight.png");
    expect(block).not.toContain("linear-gradient");
  });

  it("Glide light — headers y celdas de alto contraste", () => {
    const theme = createGridTheme(lightColors);
    expect(theme.textHeader).toBe("#18202C");
    expect(theme.textDark).toBe("#18202C");
    expect(theme.textMedium).toBe("#465160");
    expect(theme.bgHeader).toBe("#F6F8FB");
    expect(theme.bgCell).toBe("#FFFFFF");
    expect(theme.accentColor).toBe("#0166FF");
  });

  it("glass shell usa blur y tokens", () => {
    expect(String((glassSidebar as Record<string, unknown>).backdropFilter)).toContain("blur");
    expect(String((glassContent as Record<string, unknown>).backdropFilter)).toContain("blur");
    const tabs = glassTabsSecondaryPanelSx as Record<string, unknown>;
    expect(String(tabs.backgroundColor)).toContain(CSS_VAR_NAMES.surfacePanel.replace("--", ""));
    expect(String(tabs.backdropFilter)).toContain("blur");
  });

  it("MRT head usa surface table header", () => {
    const mrt = readSrc("styles/mrtGlassDataTablePreset.ts");
    expect(mrt).toContain("surfaceTableHeader");
  });
});
