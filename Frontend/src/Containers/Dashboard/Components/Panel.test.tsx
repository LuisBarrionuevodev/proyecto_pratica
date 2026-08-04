/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  IndicadoresEjecutivoResponse,
  IndicadoresNoRealizadasResponse,
  IndicadoresPendientesResponse,
  IndicadoresProductividadResponse,
  IndicadoresRiesgoResponse,
} from "../../../api/indicadoresApi";
import Panel from "./Panel";

const panelPath = resolve(fileURLToPath(new URL(".", import.meta.url)), "Panel.tsx");

const theme = createTheme();

function renderPanel() {
  return renderToStaticMarkup(
    <ThemeProvider theme={theme}>
      <Panel />
    </ThemeProvider>
  );
}

const ejecutivoMock: IndicadoresEjecutivoResponse = {
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

const riesgoMock: IndicadoresRiesgoResponse = {
  top_rubros: [{ rubro: "Panadería", cantidad: 3 }],
  top_motivos_notificacion: [{ motivo: "Habilitación", cantidad: 2 }],
  top_motivos_comprobacion: [],
  decomiso_kg_por_rubro: [],
};

const noRealizadasMock: IndicadoresNoRealizadasResponse = {
  por_tipo: {
    inspeccion: 1,
    reinspeccion_oficio: 0,
    reinspeccion_notificacion: 1,
    denuncia: 0,
  },
  top_contraproducencias: [{ contraproducencia: "LOCAL CERRADO", cantidad: 1 }],
  distritos_con_mas_no_realizadas: [],
};

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
  inspectores_no_realizadas: [],
  actas_por_inspector: [],
};

type HookState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const hookState = {
  ejecutivo: { data: null, loading: true, error: null } as HookState<IndicadoresEjecutivoResponse>,
  pendientes: { data: null, loading: true, error: null } as HookState<IndicadoresPendientesResponse>,
  riesgo: { data: null, loading: true, error: null } as HookState<IndicadoresRiesgoResponse>,
  noRealizadas: {
    data: null,
    loading: true,
    error: null,
  } as HookState<IndicadoresNoRealizadasResponse>,
  productividad: {
    data: null,
    loading: true,
    error: null,
  } as HookState<IndicadoresProductividadResponse>,
};

vi.mock("@mui/x-charts/BarChart", () => ({
  BarChart: () => null,
}));

vi.mock("../../../utils/exportExcelDashboard", () => ({
  exportDashboardToExcel: vi.fn(),
}));

vi.mock("../../../documentos/dashboard/downloadDashboardPdf", () => ({
  downloadDashboardPdf: vi.fn(),
}));

vi.mock("../../../api/geolocalizacionApi", () => ({
  fetchDistritosCatalogo: vi.fn().mockResolvedValue({ items: [] }),
}));

vi.mock("../../../api/gridApi", () => ({
  fetchInspectores: vi.fn().mockResolvedValue({ items: [] }),
}));

vi.mock("../hooks/useIndicadoresEjecutivo", () => ({
  useIndicadoresEjecutivo: () => hookState.ejecutivo,
}));

vi.mock("../hooks/useIndicadoresPendientes", () => ({
  useIndicadoresPendientes: () => hookState.pendientes,
}));

vi.mock("../hooks/useIndicadoresRiesgo", () => ({
  useIndicadoresRiesgo: () => hookState.riesgo,
}));

vi.mock("../hooks/useIndicadoresNoRealizadas", () => ({
  useIndicadoresNoRealizadas: () => hookState.noRealizadas,
}));

vi.mock("../hooks/useIndicadoresProductividad", () => ({
  useIndicadoresProductividad: () => hookState.productividad,
}));

function setAllLoaded() {
  hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
  hookState.pendientes = { data: pendientesMock, loading: false, error: null };
  hookState.riesgo = { data: riesgoMock, loading: false, error: null };
  hookState.noRealizadas = { data: noRealizadasMock, loading: false, error: null };
  hookState.productividad = { data: productividadMock, loading: false, error: null };
}

function setAllLoading() {
  hookState.ejecutivo = { data: null, loading: true, error: null };
  hookState.pendientes = { data: null, loading: true, error: null };
  hookState.riesgo = { data: null, loading: true, error: null };
  hookState.noRealizadas = { data: null, loading: true, error: null };
  hookState.productividad = { data: null, loading: true, error: null };
}

describe("IND-QA.1 — Dashboard Panel", () => {
  beforeEach(() => {
    setAllLoading();
  });

  it("importa DashboardActasPorTipoSection en Panel.tsx", () => {
    const src = readFileSync(panelPath, "utf8");
    expect(src).toContain('from "./DashboardActasPorTipoSection"');
    expect(src).toContain("<DashboardActasPorTipoSection");
  });

  it("muestra loader mientras los hooks cargan", () => {
    const html = renderPanel();
    expect(html).toContain("Cargando indicadores");
    expect(html).not.toContain("Overview operativo");
  });

  it("renderiza secciones principales cuando los hooks devuelven datos", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).toContain("Overview operativo");
    expect(html).toContain("Actas labradas por tipo");
    expect(html).toContain("Operativo / pendientes");
    expect(html).toContain("Riesgo bromatológico");
    expect(html).toContain("No realizadas");
    expect(html).toContain("Productividad");
  });

  it("no crashea si un hook devuelve error parcial", () => {
    setAllLoaded();
    hookState.ejecutivo = { data: null, loading: false, error: "No se pudo cargar el resumen ejecutivo." };
    const html = renderPanel();
    expect(html).toContain("No se pudo cargar el resumen ejecutivo.");
    expect(html).toContain("Actas labradas por tipo");
  });

  it("no muestra botón Exportar KPIs", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).not.toContain("Exportar KPIs");
  });

  it("muestra botón Exportar PDF", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).toContain("Exportar PDF");
  });

  it("deshabilita Exportar PDF mientras carga inicial", () => {
    const html = renderPanel();
    expect(html).toContain("Exportar PDF");
    expect(html).toMatch(/disabled/);
  });

  it("habilita Exportar PDF con datos cargados", () => {
    setAllLoaded();
    const html = renderPanel();
    const exportBtn = html.match(/<button[^>]*Exportar PDF[^<]*<\/button>/);
    expect(exportBtn?.[0] ?? "").not.toMatch(/disabled/);
  });

  it("Panel usa buildDashboardExportPayload y downloadDashboardPdf", () => {
    const src = readFileSync(panelPath, "utf8");
    expect(src).toContain("buildDashboardExportPayload");
    expect(src).not.toContain("exportDashboardToExcel");
    expect(src).toContain("downloadDashboardPdf");
    expect(src).toContain("Exportar PDF");
    expect(src).toContain("useMemo(() => {");
    expect(src).toContain("indicadoresParams");
  });

  it("muestra los 5 KPIs de pendientes cuando hay datos", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).toContain("Relevamientos pendientes");
    expect(html).toContain("Pendientes geolocalización");
  });
});
