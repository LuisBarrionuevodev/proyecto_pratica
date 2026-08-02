import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IActuacionListItem, IActuacionesListResponse } from "../../../api/actuacionesListApi";
import { fetchAllActuacionesForExport } from "../../../api/actuacionesExportApi";
import { buildActuacionesExportFiltersFromMeta } from "./buildActuacionesFiltroPayload";
import { buildActuacionesNormalizedExcelRows } from "./actuacionesExportNormalizedRows";
import { buildActuacionesVisualPdfRows } from "./actuacionesExportVisualRows";

const getActuacionesFiltered = vi.fn();

vi.mock("../../../api/actuacionesListApi", () => ({
  getActuacionesFiltered: (...args: unknown[]) => getActuacionesFiltered(...args),
}));

function listResponse(items: IActuacionListItem[], total = items.length): IActuacionesListResponse {
  return {
    items,
    meta: {
      total,
      page: 1,
      page_size: 500,
      desde: null,
      hasta: null,
      tipo: null,
      contraproducencia: null,
      orden_trabajo: null,
    },
  };
}

function baseRow(overrides: Partial<IActuacionListItem> = {}): IActuacionListItem {
  return {
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-05-27",
    rubro_nombre: null,
    inspector1: null,
    inspector2: null,
    inspector3: null,
    calle: null,
    numero: null,
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    acta_inspeccion_num: null,
    acta_notificacion_num: null,
    notificacion_motivo_1: null,
    notificacion_motivo_2: null,
    notificacion_motivo_3: null,
    acta_comprobacion_num: null,
    comprobacion_motivo: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    decomiso_kilos_total: null,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
    ...overrides,
  };
}

describe("DOCS-EXP.4 — export dataset Actuaciones", () => {
  beforeEach(() => {
    getActuacionesFiltered.mockReset();
  });

  describe("fetchAllActuacionesForExport", () => {
    it("propaga q al API cuando el filtro lo incluye", async () => {
      getActuacionesFiltered.mockResolvedValueOnce(listResponse([baseRow()]));

      await fetchAllActuacionesForExport({
        q: "123456",
        desde: null,
        hasta: null,
        tipo: null,
        contraproducencia: null,
        orden_trabajo: null,
      });

      expect(getActuacionesFiltered).toHaveBeenCalledWith(
        expect.objectContaining({ q: "123456", page: 1, page_size: 500 })
      );
    });

    it("no envía q vacío cuando no hay búsqueda específica", async () => {
      getActuacionesFiltered.mockResolvedValueOnce(listResponse([baseRow()]));

      await fetchAllActuacionesForExport({
        q: null,
        desde: "2026-01-01",
        hasta: "2026-01-31",
        tipo: null,
        contraproducencia: null,
        orden_trabajo: null,
      });

      const call = getActuacionesFiltered.mock.calls[0][0] as Record<string, unknown>;
      expect(call.q == null).toBe(true);
      expect(call.desde).toBe("2026-01-01");
    });
  });

  describe("buildActuacionesExportFiltersFromMeta", () => {
    it("con q activo replica filtros del listado y omite período del diálogo", () => {
      expect(
        buildActuacionesExportFiltersFromMeta(
          {
            total: 1,
            page: 1,
            page_size: 50,
            desde: null,
            hasta: null,
            tipo: null,
            contraproducencia: null,
            orden_trabajo: null,
            q: "Corrientes",
            busqueda_global: true,
          },
          { desde: "2026-06-01", hasta: "2026-06-30" }
        )
      ).toEqual({
        q: "Corrientes",
        desde: null,
        hasta: null,
        tipo: null,
        contraproducencia: null,
        orden_trabajo: null,
      });
    });

    it("sin q usa rango del diálogo de exportación", () => {
      expect(
        buildActuacionesExportFiltersFromMeta(
          {
            total: 10,
            page: 1,
            page_size: 50,
            desde: "2026-01-01",
            hasta: "2026-01-31",
            tipo: "INSPECCION",
            contraproducencia: null,
            orden_trabajo: null,
            q: null,
          },
          { desde: "2026-02-01", hasta: "2026-02-28" }
        )
      ).toEqual({
        q: null,
        desde: "2026-02-01",
        hasta: "2026-02-28",
        tipo: "INSPECCION",
        contraproducencia: null,
        orden_trabajo: null,
      });
    });
  });

  describe("domicilio operativo visual en export", () => {
    it("Excel prioriza domicilio_texto del API", () => {
      const [row] = buildActuacionesNormalizedExcelRows([
        baseRow({
          domicilio_texto: "San Martín 2869",
          calle: "raw",
          calle_normalizada: "Otra",
          numero: "1",
        } as IActuacionListItem),
      ]);
      expect(row.Domicilio).toBe("San Martín 2869");
    });

    it("Excel usa normalizada antes que raw sin domicilio_texto", () => {
      const [row] = buildActuacionesNormalizedExcelRows([
        baseRow({
          calle_estado: "OK",
          calle_normalizada: "San Martín",
          calle: "calle raw",
          numero: "2869",
        }),
      ]);
      expect(row.Domicilio).toBe("San Martín 2869");
    });

    it("PDF visual usa domicilio operativo", () => {
      const [row] = buildActuacionesVisualPdfRows([
        baseRow({
          domicilio_texto: "Maipú 500",
          calle: "raw",
          numero: "1",
          rubro_nombre: "Kiosco",
        } as IActuacionListItem),
      ]);
      expect(row.domicilioRubro).toBe("Maipú 500 · Kiosco");
    });

    it("no altera otros campos del Excel", () => {
      const [row] = buildActuacionesNormalizedExcelRows([
        baseRow({
          domicilio_texto: "San Martín 100",
          tipo_actuacion: "REINSPECCION",
          contraproducencia: "LOCAL CERRADO",
          acta_inspeccion_num: "111111",
          expediente_numero: "99",
          expediente_anio: 2026,
          oficio_numero: "12",
          oficio_anio: 2026,
          inspector1: "Pérez",
        } as IActuacionListItem),
      ]);
      expect(row["Tipo actuación"]).toBe("REINSPECCION");
      expect(row.Contraproducencia).toBe("LOCAL CERRADO");
      expect(row["Acta inspección Nº"]).toBe("111111");
      expect(row.Expediente).toBe("99/2026");
      expect(row.Oficio).toBe("12/2026");
      expect(row.Inspectores).toBe("Pérez");
    });
  });
});
