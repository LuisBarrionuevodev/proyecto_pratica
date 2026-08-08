/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
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
  distritos_con_mas_pendientes: [
    {
      distrito_id: 1,
      distrito_codigo: "C",
      distrito_nombre: "Centro",
      relevamientos: 1,
      denuncias: 0,
      reinspecciones_oficio: 2,
      reinspecciones_notificacion: 3,
      sin_geolocalizacion: 0,
      total: 6,
    },
  ],
};

function renderSection(data: IndicadoresPendientesResponse | null) {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <DashboardPendientesSection data={data} loading={false} error={null} />
    </ThemeProvider>
  );
}

describe("DashboardPendientesSection", () => {
  it("muestra los 3 KPIs visibles y el título actualizado", () => {
    const html = renderSection(pendientesMock);
    expect(html).toContain("Operativo / Pendientes actuales");
    expect(html).toContain("Relevamientos pendientes");
    expect(html).toContain("Reins. oficio pendientes");
    expect(html).toContain("Reins. notificación pendientes");
    expect(html).not.toContain("Denuncias pendientes");
    expect(html).not.toContain("Pendientes geolocalización");
    expect(html).not.toContain("Pendientes actuales al momento de consulta.");
  });

  it("tabla distritos renderiza columnas MRT sin denuncia ni geolocalización", () => {
    const html = renderSection(pendientesMock);
    expect(html).toContain("Distrito");
    expect(html).toContain("Total");
    expect(html).toContain("Relev.");
    expect(html).toContain("Reins. oficio");
    expect(html).toContain("Reins. notif.");
    expect(html).toContain("Centro (C)");
    expect(html).not.toContain("Sin geo");
    expect(html).not.toContain("Denuncia");
    expect(html).not.toContain("Geolocalización");
  });

  it("empty state de distritos no menciona período", () => {
    const html = renderSection({
      ...pendientesMock,
      distritos_con_mas_pendientes: [],
    });
    expect(html).toContain("Sin pendientes agrupados por distrito.");
    expect(html).not.toContain("período");
  });
});

describe("DashboardDistritosPendientesTable read-only", () => {
  const tableSrc = readFileSync(
    resolve(__dirname, "./DashboardDistritosPendientesTable.tsx"),
    "utf8"
  );

  it("usa MRT read-only sin toolbar, filtros ni acciones", () => {
    expect(tableSrc).toContain("useMaterialReactTable");
    expect(tableSrc).toContain("enableColumnFilters: false");
    expect(tableSrc).toContain("enableGlobalFilter: false");
    expect(tableSrc).toContain("enableRowActions: false");
    expect(tableSrc).toContain('display: "none"');
    expect(tableSrc).toContain("MRT_READ_ONLY_BANDEJA");
    expect(tableSrc).toContain("pageSize: DEFAULT_PAGE_SIZE");
  });
});
