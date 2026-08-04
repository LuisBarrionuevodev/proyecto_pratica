import { describe, expect, it } from "vitest";

import { buildDashboardExportPayload } from "../Containers/Dashboard/utils/buildDashboardExportPayload";
import type { DashboardExportPayload } from "../Containers/Dashboard/utils/buildDashboardExportPayload";
import { exportDashboardToExcel, listDashboardWorkbookSheetNames } from "./exportExcelDashboard";

const fullPayload: DashboardExportPayload = {
  meta: {
    periodoLabel: "Mensual (2026-01-01 → 2026-01-31)",
    distritoLabel: "Centro",
    inspectorLabel: "García",
  },
  resumenKpis: [{ title: "Actuaciones realizadas", value: 10 }],
  ejecutivo: null,
  pendientes: null,
  actasPorTipo: {
    inspeccion: 2,
    notificacion: 1,
    comprobacion: 1,
    clausura: 0,
    decomiso: 0,
  },
  pendientesDistritos: [
    {
      distrito_id: 1,
      distrito_codigo: "C",
      distrito_nombre: "Centro",
      relevamientos: 1,
      denuncias: 2,
      reinspecciones_oficio: 0,
      reinspecciones_notificacion: 1,
      sin_geolocalizacion: 3,
      total: 7,
    },
  ],
  riesgo: {
    top_rubros: [{ rubro: "Panadería", cantidad: 3 }],
    top_motivos_notificacion: [{ motivo: "Habilitación", cantidad: 2 }],
    top_motivos_comprobacion: [],
    decomiso_kg_por_rubro: [{ rubro: "Carnicería", kg: 5.5 }],
  },
  mercaderiaDecomisadaKg: 12,
  noRealizadas: {
    por_tipo: {
      inspeccion: 1,
      reinspeccion_oficio: 0,
      reinspeccion_notificacion: 1,
      denuncia: 0,
    },
    top_contraproducencias: [{ contraproducencia: "LOCAL CERRADO", cantidad: 1 }],
    distritos_con_mas_no_realizadas: [{ distrito_id: 1, distrito_codigo: "C", distrito_nombre: "Centro", cantidad: 2 }],
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
        tipo_principal: "INSPECCION",
      },
    ],
    inspectores_no_realizadas: [],
    actas_por_inspector: [],
  },
};

const emptyBlocksPayload: DashboardExportPayload = {
  meta: {
    periodoLabel: "Semanal (2026-01-01 → 2026-01-07)",
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

describe("exportExcelDashboard", () => {
  it("crea las 6 hojas esperadas", () => {
    const names = listDashboardWorkbookSheetNames(fullPayload);
    expect(names).toEqual([
      "Resumen KPIs",
      "Actas por tipo",
      "Pendientes por distrito",
      "Riesgo",
      "No realizadas",
      "Productividad",
    ]);
  });

  it("exportDashboardToExcel no lanza con payload completo", () => {
    expect(() => exportDashboardToExcel(fullPayload)).not.toThrow();
  });

  it("respeta filtros en hoja Resumen KPIs", () => {
    const names = listDashboardWorkbookSheetNames(fullPayload);
    expect(names[0]).toBe("Resumen KPIs");
    const payload = buildDashboardExportPayload({
      periodoLabel: fullPayload.meta.periodoLabel,
      distritoLabel: fullPayload.meta.distritoLabel,
      inspectorLabel: fullPayload.meta.inspectorLabel,
      ejecutivo: null,
      pendientes: null,
      riesgo: null,
      noRealizadas: null,
      noRealizadasTotal: null,
      productividad: null,
    });
    expect(payload.meta.periodoLabel).toContain("Mensual");
    expect(payload.meta.distritoLabel).toBe("Centro");
    expect(payload.meta.inspectorLabel).toBe("García");
  });

  it("no crashea con bloques vacíos", () => {
    expect(() => listDashboardWorkbookSheetNames(emptyBlocksPayload)).not.toThrow();
    const names = listDashboardWorkbookSheetNames(emptyBlocksPayload);
    expect(names).toHaveLength(6);
    expect(() => exportDashboardToExcel(emptyBlocksPayload)).not.toThrow();
  });

  it("no crashea con riesgo y productividad vacíos pero meta presente", () => {
    const partial: DashboardExportPayload = {
      ...emptyBlocksPayload,
      resumenKpis: [{ title: "Test", value: 1 }],
      riesgo: {
        top_rubros: [],
        top_motivos_notificacion: [],
        top_motivos_comprobacion: [],
        decomiso_kg_por_rubro: [],
      },
      productividad: {
        inspectores_realizadas: [],
        inspectores_no_realizadas: [],
        actas_por_inspector: [],
      },
    };
    expect(() => listDashboardWorkbookSheetNames(partial)).not.toThrow();
  });
});
