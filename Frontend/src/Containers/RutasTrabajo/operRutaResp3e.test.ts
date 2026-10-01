import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-RESP.3-E — mapa final y publicación mobile-first", () => {
  it("vista mapa final evita overflow horizontal y apila en xs", () => {
    const view = read("src/Containers/RutasTrabajo/views/RutasMapaOperativoView.tsx");
    expect(view).toContain('data-testid="mapa-final-view"');
    expect(view).toContain('overflowX: "hidden"');
    expect(view).toContain('direction={{ xs: "column", md: "row" }}');
    expect(view).toContain('data-testid="mapa-final-main-layout"');
  });

  it("layout tokens definen alturas responsive mapa y panel resumen", () => {
    const layout = read("src/Containers/RutasTrabajo/mapaFinalLayout.ts");
    expect(layout).toContain("MAPA_FINAL_MAP_HEIGHT_SX");
    expect(layout).toContain("MAPA_FINAL_RESUMEN_PANEL_SX");
    expect(layout).toContain("min(52vh");
    expect(layout).toContain('xs: "100%"');
  });

  it("MapaRutaTrabajo contiene el mapa sin desbordar ancho", () => {
    const mapa = read("src/Containers/RutasTrabajo/Components/MapaRutaTrabajo.tsx");
    expect(mapa).toContain('maxWidth: "100%"');
    expect(mapa).toContain('minWidth: 0');
  });

  it("panel lateral de grupos legible en móvil", () => {
    const lateral = read("src/Containers/RutasTrabajo/Components/MapaFinalResumenLateral.tsx");
    expect(lateral).toContain('data-testid="mapa-final-resumen-lateral"');
    expect(lateral).toContain('flexWrap: "wrap"');
    expect(lateral).toContain('direction={{ xs: "column", sm: "row" }}');
  });

  it("publicar sigue en header compacto, no en vista mapa", () => {
    const view = read("src/Containers/RutasTrabajo/views/RutasMapaOperativoView.tsx");
    expect(view).not.toContain('data-testid="mapa-final-publicar-action"');
    const header = read("src/Containers/RutasTrabajo/Components/RutaTrabajoCompactHeader.tsx");
    expect(header).toContain('data-testid="header-publicar-ruta"');
    expect(header).toContain("Volver a asignación");
  });
});
