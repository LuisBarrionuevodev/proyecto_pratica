import { describe, expect, it } from "vitest";

import type { DashboardExportPayload } from "./buildDashboardExportPayload";
import {
  buildDashboardPdfModel,
  DASHBOARD_PDF_EMPTY_MESSAGE,
} from "./dashboardPdfMappers";

const fullPayload: DashboardExportPayload = {
  meta: {
    periodoLabel: "Mensual (2026-01-01 → 2026-01-31)",
    distritoLabel: "Centro",
    inspectorLabel: "García",
  },
  resumenKpis: [],
  ejecutivo: {
    periodo: { desde: "2026-01-01", hasta: "2026-01-31" },
    kpis: {
      actuaciones_realizadas: 10,
      actas_labradas: 5,
      inspecciones_realizadas: 3,
      reinspecciones_notificacion_realizadas: 2,
      reinspecciones_oficio_realizadas: 3,
      ratificaciones_clausura_realizadas: 1,
      ratificaciones_decomiso_realizadas: 0,
      verificar_informar_realizadas: 1,
      mercaderia_decomisada_kg: 12.5,
    },
    actas_por_tipo: {
      inspeccion: 2,
      notificacion: 1,
      comprobacion: 1,
      clausura: 0,
      decomiso: 1,
    },
  },
  pendientes: {
    kpis: {
      relevamientos_pendientes: 1,
      reinspecciones_oficio_pendientes: 2,
      reinspecciones_notificacion_pendientes: 3,
      denuncias_pendientes: 4,
      pendientes_geolocalizacion: 5,
    },
    distritos_con_mas_pendientes: [],
  },
  actasPorTipo: {
    inspeccion: 2,
    notificacion: 1,
    comprobacion: 1,
    clausura: 0,
    decomiso: 1,
  },
  pendientesDistritos: [],
  riesgo: {
    top_rubros: [{ rubro: "Panadería", cantidad: 3 }],
    top_motivos_notificacion: [{ motivo: "Habilitación", cantidad: 2 }],
    top_motivos_comprobacion: [],
    decomiso_kg_por_rubro: [{ rubro: "Carnicería", kg: 5.5 }],
  },
  mercaderiaDecomisadaKg: 12.5,
  noRealizadas: {
    por_tipo: {
      inspeccion: 1,
      reinspeccion_oficio: 0,
      reinspeccion_notificacion: 1,
      denuncia: 0,
    },
    top_contraproducencias: [{ contraproducencia: "Local cerrado", cantidad: 1 }],
    distritos_con_mas_no_realizadas: [
      { distrito_id: 1, distrito_codigo: "C", distrito_nombre: "Centro", cantidad: 2 },
    ],
    total: 2,
    contraproducencias_resumen: [
      { bucket: "local_cerrado", label: "Local cerrado", cantidad: 1 },
      { bucket: "no_existe", label: "No existe", cantidad: 0 },
      { bucket: "no_se_ratifico", label: "No se ratificó", cantidad: 1 },
      { bucket: "clima", label: "Clima", cantidad: 0 },
      { bucket: "otras", label: "Otras", cantidad: 0 },
    ],
  },
  noRealizadasTotal: 2,
  productividad: {
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
  },
};

const emptyPayload: DashboardExportPayload = {
  meta: {
    periodoLabel: "Semanal",
    distritoLabel: "Todos",
    inspectorLabel: "Todos",
  },
  resumenKpis: [],
  ejecutivo: null,
  pendientes: null,
  actasPorTipo: null,
  pendientesDistritos: [],
  riesgo: null,
  mercaderiaDecomisadaKg: null,
  noRealizadas: null,
  noRealizadasTotal: null,
  productividad: null,
};

describe("buildDashboardPdfModel", () => {
  it("arma secciones con KPIs ejecutivos y pendientes", () => {
    const model = buildDashboardPdfModel(
      fullPayload,
      "2026-01-01",
      "2026-01-31",
      "04/08/2026",
      "01/01/2026 al 31/01/2026"
    );
    expect(model.title).toBe("Informe de Indicadores Operativos");
    expect(model.ejecutivoKpis).toHaveLength(8);
    expect(model.ejecutivoKpis.find((k) => k.label.includes("oficio realizadas"))?.value).toBe("3");
    expect(model.pendientesKpis).toHaveLength(3);
    expect(model.distritoLabel).toBe("Centro");
    expect(model.inspectorLabel).toBe("García");
  });

  it("incluye actas por tipo, riesgo, no realizadas y productividad", () => {
    const model = buildDashboardPdfModel(
      fullPayload,
      "2026-01-01",
      "2026-01-31",
      "04/08/2026",
      "01/01/2026 al 31/01/2026"
    );
    expect(model.actasPorTipo.rows).toHaveLength(5);
    expect(model.riesgoRubros.rows).toHaveLength(1);
    expect(model.noRealizadasTotal).toBe("2");
    expect(model.noRealizadasContraproducencias.headers).toEqual([
      "Contraproducencia",
      "Cantidad",
      "%",
    ]);
    expect(model.noRealizadasContraproducencias.rows.length).toBeGreaterThan(0);
    expect(model.productividadRealizadas.rows).toHaveLength(1);
  });

  it("bloques vacíos no crashean y dejan secciones sin filas", () => {
    const model = buildDashboardPdfModel(
      emptyPayload,
      "2026-01-01",
      "2026-01-07",
      "04/08/2026",
      "01/01/2026 al 07/01/2026"
    );
    expect(model.ejecutivoKpis).toHaveLength(0);
    expect(model.pendientesKpis).toHaveLength(0);
    expect(model.actasPorTipo.rows).toHaveLength(0);
    expect(model.riesgoRubros.rows).toHaveLength(0);
    expect(model.noRealizadasTotal).toBeNull();
    expect(DASHBOARD_PDF_EMPTY_MESSAGE).toContain("Sin datos");
  });

  it("no realizadas prioriza contraproducencias con Otros y sin desglose por tipo", () => {
    const payload: DashboardExportPayload = {
      ...fullPayload,
      noRealizadas: {
        por_tipo: {
          inspeccion: 5,
          reinspeccion_oficio: 0,
          reinspeccion_notificacion: 0,
          denuncia: 0,
        },
        top_contraproducencias: [
          { contraproducencia: "Local cerrado", cantidad: 3 },
          { contraproducencia: "Clima", cantidad: 1 },
        ],
        distritos_con_mas_no_realizadas: [],
        total: 5,
        contraproducencias_resumen: [
          { bucket: "local_cerrado", label: "Local cerrado", cantidad: 3 },
          { bucket: "no_existe", label: "No existe", cantidad: 0 },
          { bucket: "no_se_ratifico", label: "No se ratificó", cantidad: 0 },
          { bucket: "clima", label: "Clima", cantidad: 1 },
          { bucket: "otras", label: "Otras", cantidad: 1 },
        ],
      },
      noRealizadasTotal: 5,
    };
    const model = buildDashboardPdfModel(
      payload,
      "2026-01-01",
      "2026-01-31",
      "04/08/2026",
      "01/01/2026 al 31/01/2026"
    );
    expect(model.noRealizadasTotal).toBe("5");
    expect(model.noRealizadasContraproducencias.rows.some((r) => r.label === "Otras")).toBe(true);
    expect(
      (model as { noRealizadasPorTipo?: unknown }).noRealizadasPorTipo
    ).toBeUndefined();
  });

  it("limita productividad a top 10 y agrega nota de truncado", () => {
    const manyInspectors = Array.from({ length: 12 }, (_, i) => ({
      inspector_id: i + 1,
      inspector: `Inspector ${i + 1}`,
      total_realizadas: 10 - i,
      inspecciones: 5,
      reinspecciones_oficio: 0,
      reinspecciones_notificacion: 0,
      denuncias: 0,
      tipo_principal: "INSPECCION",
    }));
    const payload: DashboardExportPayload = {
      ...fullPayload,
      productividad: {
        inspectores_realizadas: manyInspectors,
        inspectores_no_realizadas: [],
        actas_por_inspector: [],
      },
    };
    const model = buildDashboardPdfModel(
      payload,
      "2026-01-01",
      "2026-01-31",
      "04/08/2026",
      "01/01/2026 al 31/01/2026"
    );
    expect(model.productividadRealizadas.rows).toHaveLength(10);
    expect(model.productividadTruncatedNote).toContain("Excel");
  });
});
