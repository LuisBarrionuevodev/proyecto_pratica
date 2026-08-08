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
    inspecciones_realizadas: 3,
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
  total: 2,
  contraproducencias_resumen: [
    { bucket: "local_cerrado", label: "Local cerrado", cantidad: 1 },
    { bucket: "no_existe", label: "No existe", cantidad: 0 },
    { bucket: "no_se_ratifico", label: "No se ratificó", cantidad: 1 },
    { bucket: "clima", label: "Clima", cantidad: 0 },
    { bucket: "otras", label: "Otras", cantidad: 0 },
  ],
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
      otras: 0,
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

vi.mock("./DashboardProductividadSectionLazy", async () => {
  const { DashboardProductividadSection } = await import("./DashboardProductividadSection");
  return {
    DashboardProductividadSectionLazy: DashboardProductividadSection,
  };
});

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

  it("muestra loader global solo en carga inicial total", () => {
    const html = renderPanel();
    expect(html).toContain("Cargando indicadores");
    expect(html).not.toContain("Overview operativo");
  });

  it("renderiza estructura aunque solo Ejecutivo terminó", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: null, loading: true, error: null };
    hookState.riesgo = { data: null, loading: true, error: null };
    hookState.noRealizadas = { data: null, loading: true, error: null };
    hookState.productividad = { data: null, loading: true, error: null };

    const html = renderPanel();
    expect(html).not.toContain("Cargando indicadores");
    expect(html).toContain("Overview operativo");
    expect(html).toContain("Actas labradas por tipo");
    expect(html).toContain("Cargando pendientes");
    expect(html).toContain("Cargando riesgo");
    expect(html).toContain("Cargando productividad");
  });

  it("muestra loader de sección Pendientes mientras carga", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: null, loading: true, error: null };
    hookState.riesgo = { data: riesgoMock, loading: false, error: null };
    hookState.noRealizadas = { data: noRealizadasMock, loading: false, error: null };
    hookState.productividad = { data: productividadMock, loading: false, error: null };

    const html = renderPanel();
    expect(html).toContain("Cargando pendientes");
    expect(html).not.toContain("Relevamientos pendientes");
  });

  it("muestra loader de sección Riesgo mientras carga", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: pendientesMock, loading: false, error: null };
    hookState.riesgo = { data: null, loading: true, error: null };
    hookState.noRealizadas = { data: noRealizadasMock, loading: false, error: null };
    hookState.productividad = { data: productividadMock, loading: false, error: null };

    const html = renderPanel();
    expect(html).toContain("Cargando riesgo");
    expect(html).not.toContain("Motivos de notificación");
  });

  it("muestra loader de sección Productividad mientras carga", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: pendientesMock, loading: false, error: null };
    hookState.riesgo = { data: riesgoMock, loading: false, error: null };
    hookState.noRealizadas = { data: noRealizadasMock, loading: false, error: null };
    hookState.productividad = { data: null, loading: true, error: null };

    const html = renderPanel();
    expect(html).toContain("Cargando productividad");
    expect(html).not.toContain("Pérez");
  });

  it("no usa loader global cuando ya hay datos parciales", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: null, loading: true, error: null };
    hookState.riesgo = { data: null, loading: true, error: null };
    hookState.noRealizadas = { data: null, loading: true, error: null };
    hookState.productividad = { data: null, loading: true, error: null };

    const html = renderPanel();
    expect(html).not.toContain("Cargando indicadores");
    expect(html).toContain("Overview operativo");
  });

  it("mantiene layout y overlay suave al refrescar filtros", () => {
    setAllLoaded();
    hookState.pendientes = { data: pendientesMock, loading: true, error: null };

    const html = renderPanel();
    expect(html).toContain("Overview operativo");
    expect(html).toContain("Operativo / Pendientes actuales");
    expect(html).toContain('aria-hidden="true"');
  });

  it("deshabilita Exportar PDF durante carga parcial", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: null, loading: true, error: null };
    hookState.riesgo = { data: null, loading: true, error: null };
    hookState.noRealizadas = { data: null, loading: true, error: null };
    hookState.productividad = { data: null, loading: true, error: null };

    const html = renderPanel();
    expect(html).toMatch(/disabled/);
  });

  it("renderiza Productividad al recibir datos", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).toContain("Productividad");
    expect(html).toContain("Pérez");
  });

  it("no crashea con bloques vacíos tras carga", () => {
    hookState.ejecutivo = { data: ejecutivoMock, loading: false, error: null };
    hookState.pendientes = { data: null, loading: false, error: null };
    hookState.riesgo = { data: null, loading: false, error: null };
    hookState.noRealizadas = { data: null, loading: false, error: null };
    hookState.productividad = { data: null, loading: false, error: null };

    const html = renderPanel();
    expect(html).toContain("Overview operativo");
    expect(html).not.toContain("Cargando pendientes");
  });

  it("renderiza secciones principales cuando los hooks devuelven datos", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).toContain("Overview operativo");
    expect(html).toContain("Actas labradas por tipo");
    expect(html).toContain("Operativo / Pendientes actuales");
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

  it("Panel usa buildDashboardExportPayload, lazy Productividad y carga progresiva", () => {
    const src = readFileSync(panelPath, "utf8");
    expect(src).toContain("buildDashboardExportPayload");
    expect(src).not.toContain("exportDashboardToExcel");
    expect(src).toContain("downloadDashboardPdf");
    expect(src).toContain("Exportar PDF");
    expect(src).toContain("DashboardProductividadSectionLazy");
    expect(src).toContain("DashboardSectionGate");
    expect(src).toContain("showGlobalLoader");
    expect(src).toContain("useMemo(() => {");
    expect(src).toContain("indicadoresParams");
  });

  it("muestra los 3 KPIs de pendientes cuando hay datos", () => {
    setAllLoaded();
    const html = renderPanel();
    expect(html).toContain("Relevamientos pendientes");
    expect(html).toContain("Operativo / Pendientes actuales");
    expect(html).not.toContain("Pendientes geolocalización");
    expect(html).not.toContain("Pendientes actuales al momento de consulta.");
  });
});
