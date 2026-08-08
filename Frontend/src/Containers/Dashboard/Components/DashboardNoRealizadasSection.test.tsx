/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IndicadoresNoRealizadasResponse } from "../../../api/indicadoresApi";
import { DashboardNoRealizadasSection } from "./DashboardNoRealizadasSection";

const theme = createTheme();

const noRealizadasMock: IndicadoresNoRealizadasResponse = {
  por_tipo: {
    inspeccion: 2,
    reinspeccion_oficio: 3,
    reinspeccion_notificacion: 0,
    denuncia: 0,
  },
  top_contraproducencias: [],
  distritos_con_mas_no_realizadas: [
    {
      distrito_id: 1,
      distrito_codigo: "D1",
      distrito_nombre: "Centro",
      cantidad: 5,
    },
  ],
  total: 5,
  contraproducencias_resumen: [
    { bucket: "local_cerrado", label: "Local cerrado", cantidad: 3 },
    { bucket: "no_existe", label: "No existe", cantidad: 1 },
    { bucket: "no_se_ratifico", label: "No se ratificó", cantidad: 0 },
    { bucket: "clima", label: "Clima", cantidad: 1 },
    { bucket: "otras", label: "Otras", cantidad: 0 },
  ],
};

function renderSection(data: IndicadoresNoRealizadasResponse | null, error: string | null = null) {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <DashboardNoRealizadasSection data={data} loading={false} error={error} />
    </ThemeProvider>
  );
}

describe("DashboardNoRealizadasSection", () => {
  it("no muestra card redundante No realizadas total", () => {
    const html = renderSection(noRealizadasMock);
    expect(html).not.toContain("No realizadas total");
    expect(html).not.toContain("Reins. oficio");
    expect(html).not.toContain("Inspección");
  });

  it("muestra las 5 categorías fijas de contraproducencia", () => {
    const html = renderSection(noRealizadasMock);
    expect(html).toContain("Principales contraproducencias");
    expect(html).toContain("Local cerrado");
    expect(html).toContain("No existe");
    expect(html).toContain("No se ratificó");
    expect(html).toContain("Clima");
    expect(html).toContain("Otras");
  });

  it("con total 0 muestra mensaje vacío en contraproducencias", () => {
    const html = renderSection({
      ...noRealizadasMock,
      total: 0,
      contraproducencias_resumen: noRealizadasMock.contraproducencias_resumen.map((r) => ({
        ...r,
        cantidad: 0,
      })),
    });
    expect(html).not.toContain("No realizadas total");
    expect(html).toContain("Sin no realizadas en el período seleccionado.");
  });

  it("mantiene distritos como vista secundaria", () => {
    const html = renderSection(noRealizadasMock);
    expect(html).toContain("Distritos con más no realizadas");
    expect(html).toContain("Centro");
  });
});
