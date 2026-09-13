/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("MAPA-UX.2 — layout y jerarquía visual", () => {
  it("MapPage estira mapa y panel en desktop", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain('alignItems: "stretch"');
    expect(mapPage).toContain("fillParentHeight={!mapExpanded}");
    expect(mapPage).not.toContain("OperativoPeriodoLabel");
  });

  it("MapaCanvas soporta fillParentHeight con flex stretch y minHeight", () => {
    const canvas = read("src/Containers/Mapa/Components/MapaCanvas.tsx");
    expect(canvas).toContain("fillParentHeight");
    expect(canvas).toContain("fillParentHeight ? 1 : undefined");
    expect(canvas).toContain("minHeight: mapExpanded");
    expect(canvas).toContain("fillParentHeight={fillParentHeight}");
  });

  it("PanelResumenOperativo usa estilos de jerarquía MAPA-UX.2", () => {
    const panel = read("src/Containers/Mapa/Components/PanelResumenOperativo.tsx");
    expect(panel).toContain("mapaOperativoPanelTitleSx");
    expect(panel).toContain("mapaOperativoMetricRowLabelSx");
    expect(panel).toContain("mapaOperativoMetricRowValueSx");
    expect(panel).toContain("mapaOperativoLegendLabelSx");
    expect(panel).toContain("mapaOperativoHeroValueSx");
  });
});
