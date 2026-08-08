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
      otras: 0,
      tipo_principal: "Reinspección oficio",
    },
  ],
  inspectores_no_realizadas: [
    {
      inspector_id: 2,
      inspector: "Gómez",
      total_no_realizadas: 2,
      contraproducencia_principal: "Local cerrado",
      local_cerrado: 1,
      no_existe: 0,
      no_se_ratifico: 0,
      clima: 0,
      otras: 1,
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
    expect(html).toContain("Reins. oficio");
    expect(html).not.toContain("Tipo principal");
    expect(html).not.toContain("Denuncias");
  });

  it("realizadas: total coincide con suma de columnas visibles", () => {
    const html = renderSection(productividadMock);
    expect(html).toContain("Otras");
    expect(html).toContain("5");
  });

  it("no realizadas por inspector muestra columnas de contraproducencia", () => {
    const html = renderSection(productividadMock);
    expect(html).toContain("Actuaciones no realizadas por inspector");
    expect(html).toContain("Gómez");
    expect(html).toContain("Local cerrado");
    expect(html).toContain("No existe");
    expect(html).toContain("No se ratificó");
    expect(html).toContain("Clima");
    expect(html).not.toContain("Contraproducencia principal");
  });

  it("muestra 0 en celdas numéricas sin ocultar columnas", () => {
    const html = renderSection({
      ...productividadMock,
      inspectores_realizadas: [
        {
          inspector_id: 9,
          inspector: "Cero",
          total_realizadas: 0,
          inspecciones: 0,
          reinspecciones_oficio: 0,
          reinspecciones_notificacion: 0,
          denuncias: 0,
          otras: 0,
          tipo_principal: "Sin datos",
        },
      ],
    });
    expect(html).toContain("Reins. oficio");
    expect(html).toContain("Cero");
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
