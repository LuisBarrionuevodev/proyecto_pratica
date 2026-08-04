/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IndicadoresProductividadResponse } from "../../../api/indicadoresApi";
import { DashboardProductividadSection } from "./DashboardProductividadSection";

const theme = createTheme();

const productividadMock: IndicadoresProductividadResponse = {
  inspectores_realizadas: [
    {
      inspector_id: 1,
      inspector: "Pérez",
      total_realizadas: 5,
      inspecciones: 3,
      reinspecciones_oficio: 1,
      reinspecciones_notificacion: 1,
      denuncias: 0,
      tipo_principal: "INSPECCION",
    },
  ],
  inspectores_no_realizadas: [
    {
      inspector_id: 2,
      inspector: "Gómez",
      total_no_realizadas: 2,
      contraproducencia_principal: "Local cerrado",
      inspecciones: 1,
      reinspecciones_oficio: 0,
      reinspecciones_notificacion: 1,
      denuncias: 0,
    },
  ],
  actas_por_inspector: [
    {
      inspector_id: 1,
      inspector: "Pérez",
      notificacion: 1,
      comprobacion: 0,
      clausura: 0,
      decomiso: 0,
      total_actas: 1,
    },
  ],
};

function renderSection(data: IndicadoresProductividadResponse | null, error: string | null = null) {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <DashboardProductividadSection data={data} loading={false} error={error} />
    </ThemeProvider>
  );
}

describe("DashboardProductividadSection", () => {
  it("renderiza las tres tablas cuando hay datos", () => {
    const html = renderSection(productividadMock);
    expect(html).toContain("Actuaciones realizadas por inspector");
    expect(html).toContain("Actuaciones no realizadas por inspector");
    expect(html).toContain("Actas labradas por inspector");
    expect(html).toContain("Pérez");
    expect(html).toContain("Gómez");
    expect(html).toContain("Contraproducencia");
  });

  it("no crashea con payload vacío", () => {
    const html = renderSection({
      inspectores_realizadas: [],
      inspectores_no_realizadas: [],
      actas_por_inspector: [],
    });
    expect(html).toContain("Productividad");
    expect(html).toContain("Sin actuaciones realizadas por inspector");
  });

  it("no crashea con data null", () => {
    const html = renderSection(null);
    expect(html).toContain("Productividad");
  });
});
