/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IndicadoresPendientesResponse } from "../../../api/indicadoresApi";
import { DashboardPendientesSection } from "./DashboardPendientesSection";

const theme = createTheme();

const pendientesMock: IndicadoresPendientesResponse = {
  kpis: {
    relevamientos_pendientes: 1,
    reinspecciones_oficio_pendientes: 2,
    reinspecciones_notificacion_pendientes: 3,
    denuncias_pendientes: 4,
    pendientes_geolocalizacion: 5,
  },
  distritos_con_mas_pendientes: [],
};

function renderSection(data: IndicadoresPendientesResponse | null) {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <DashboardPendientesSection data={data} loading={false} error={null} />
    </ThemeProvider>
  );
}

describe("DashboardPendientesSection", () => {
  it("muestra los 5 KPIs de pendientes", () => {
    const html = renderSection(pendientesMock);
    expect(html).toContain("Relevamientos pendientes");
    expect(html).toContain("Reins. oficio pendientes");
    expect(html).toContain("Reins. notificación pendientes");
    expect(html).toContain("Denuncias pendientes");
    expect(html).toContain("Pendientes geolocalización");
  });
});
