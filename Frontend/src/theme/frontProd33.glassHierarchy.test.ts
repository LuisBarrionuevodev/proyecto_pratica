import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { darkColors, lightColors } from "./colors";
import { glassContent } from "../styles/GlassStyles";

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

describe("FRONT-PROD.3.3 — glass hierarchy & shell", () => {
  it("light: jerarquía shell < panel < elevated < input", () => {
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

  it("dark shell tokens sin cambios estructurales de referencia", () => {
    expect(darkColors.surface.sidebar).toContain("18, 18, 22");
    expect(darkColors.surface.content).toContain("18, 18, 22");
  });

  it("AppLayout usa glassContent", () => {
    const layout = readSrc("layouts/AppLayout.tsx");
    expect(layout).toContain("glassContent");
    expect(layout).not.toMatch(/backgroundColor:\s*GLASS_COLORS\.contentBg/);
  });

  it("Inicio: authenticated route + sin placa opaca global", () => {
    const inicio = readSrc("Containers/Inicio/index.tsx");
    expect(inicio).toContain("setBodyAuthenticatedRoute");
    expect(inicio).toContain('backgroundColor: "transparent"');
    expect(inicio).not.toContain("glassContent");
  });

  it("TopBar wordmark no limitado por sidebarWidth", () => {
    const topBar = readSrc("Componets/TopBar.tsx");
    expect(topBar).toContain('width: "auto"');
    expect(topBar).toMatch(/width:\s*\{\s*xs:\s*175/);
    expect(topBar).not.toContain('maxWidth: "100%"');
  });

  it("light authenticated: BackgroundInicioLight puro, sin overlay global", () => {
    const css = readSrc("index.css");
    const lightAuth = css.match(
      /\[data-theme="light"\] body\.authenticated-route\s*\{[\s\S]*?\}/
    )?.[0];
    expect(lightAuth).toBeDefined();
    expect(lightAuth).toContain("BackgroundInicioLight.png");
    expect(lightAuth).not.toContain("linear-gradient");
    expect(lightAuth).not.toContain("radial-gradient");
  });

  it("public-route usa BackgroundInicio2 sin theme ni BackgroundInicioLight", () => {
    const css = readSrc("index.css");
    const publicBlock = css.match(/body\.public-route\s*\{[\s\S]*?\}/)?.[0];
    expect(publicBlock).toBeDefined();
    expect(publicBlock).toContain("BackgroundInicio2.png");
    expect(publicBlock).not.toContain("BackgroundInicioLight");
    expect(css).not.toMatch(/\[data-theme="light"\] body\.public-route/);
    expect(css).not.toMatch(/\[data-theme="dark"\] body\.public-route/);
  });

  it("NavLeft drawer aplica glassSidebar", () => {
    const nav = readSrc("styles/NavBarStyles.ts");
    expect(nav).toContain("glassSidebar");
    expect(nav).toContain("GLASS_COLORS.textPrimary");
  });

  it("glassContent incluye blur", () => {
    const gc = glassContent as Record<string, unknown>;
    expect(String(gc.backdropFilter)).toContain("blur");
  });
});
