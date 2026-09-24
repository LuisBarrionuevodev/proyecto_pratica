/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { MapPointFeature } from "../../../api/mapApi";
import { PanelResumenOperativo } from "./PanelResumenOperativo";

const theme = createTheme();

function feature(tipo: string, id: number): MapPointFeature {
  return {
    type: "Feature",
    geometry: { type: "Point", coordinates: [-58.4, -34.6] },
    properties: { tipo_iniciador: tipo, ruta_item_id: id },
  };
}

describe("PanelResumenOperativo — OPER-ANALYTICS.4.1", () => {
  it("muestra meta operativa y desglose por tipo solo sobre ubicados", () => {
    const features = [
      feature("RELEVAMIENTO", 1),
      feature("DENUNCIA", 2),
      feature("RELEVAMIENTO", 3),
    ];

    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <PanelResumenOperativo
          features={features}
          meta={{
            total_operativos: 117,
            total_dibujables: 35,
            total_sin_geocode: 82,
            realizados: 32,
            no_realizados: 85,
            realizados_sin_geo: 17,
            no_realizados_sin_geo: 65,
          }}
        />
      </ThemeProvider>
    );

    expect(html).toContain("117");
    expect(html).toContain("Con ubicación");
    expect(html).toContain("35");
    expect(html).toContain("Por tipo de iniciador · con ubicación (3)");
    expect(html).not.toContain("Por tipo de iniciador</");
    expect(html).toContain("Realizados");
    expect(html).toContain("Leyenda del mapa");
    expect(html).toContain("Resumen operativo");
    expect(html).toContain("font-size:1.25rem");
    expect(html).toContain("font-weight:700");
    expect(html).toContain("font-weight:500");
    expect(html).toContain("color:#fff");
    expect(html).toMatch(/color:rgb\(25, 118, 210\)|color:#1976d2/);
  });
});
