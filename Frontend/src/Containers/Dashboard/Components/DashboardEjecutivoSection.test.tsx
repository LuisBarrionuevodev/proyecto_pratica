/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IndicadoresEjecutivoResponse } from "../../../api/indicadoresApi";
import { DashboardEjecutivoSection } from "./DashboardEjecutivoSection";

const theme = createTheme();

const baseEjecutivo: IndicadoresEjecutivoResponse = {
  periodo: { desde: "2026-01-01", hasta: "2026-01-31" },
  kpis: {
    actuaciones_realizadas: 10,
    actas_labradas: 5,
    reinspecciones_notificacion_realizadas: 2,
    reinspecciones_oficio_realizadas: 0,
    ratificaciones_clausura_realizadas: 1,
    ratificaciones_decomiso_realizadas: 0,
    verificar_informar_realizadas: 1,
    mercaderia_decomisada_kg: 12.5,
  },
  actas_por_tipo: {
    inspeccion: 2,
    notificacion: 1,
    comprobacion: 1,
    clausura: 1,
    decomiso: 0,
  },
};

function renderSection(data: IndicadoresEjecutivoResponse | null) {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <DashboardEjecutivoSection
        data={data}
        noRealizadasTotal={2}
        loading={false}
        error={null}
      />
    </ThemeProvider>
  );
}

describe("DashboardEjecutivoSection", () => {
  it("muestra card de reins. oficio realizadas", () => {
    const html = renderSection(baseEjecutivo);
    expect(html).toContain("Reins. oficio realizadas");
  });

  it("muestra valor de reins. oficio cuando el payload trae cantidad", () => {
    const html = renderSection({
      ...baseEjecutivo,
      kpis: { ...baseEjecutivo.kpis, reinspecciones_oficio_realizadas: 4 },
    });
    expect(html).toContain("Reins. oficio realizadas");
  });
});
