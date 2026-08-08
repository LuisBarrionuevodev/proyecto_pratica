import * as XLSX from "xlsx";
import { saveAs } from "file-saver";

import type { DashboardExportPayload } from "../Containers/Dashboard/utils/buildDashboardExportPayload";
import {
  buildContraproducenciasResumen,
  formatPorcentajeNoRealizadas,
} from "../Containers/Dashboard/utils/noRealizadasContraproducencias";

const EMPTY_ROW = "Sin datos en el período seleccionado.";

function appendSheet(
  wb: XLSX.WorkBook,
  name: string,
  rows: Record<string, string | number>[]
): void {
  const ws =
    rows.length > 0
      ? XLSX.utils.json_to_sheet(rows)
      : XLSX.utils.aoa_to_sheet([[EMPTY_ROW]]);
  XLSX.utils.book_append_sheet(wb, ws, name.slice(0, 31));
}

function appendAoaSheet(wb: XLSX.WorkBook, name: string, aoa: (string | number)[][]): void {
  const ws = aoa.length > 0 ? XLSX.utils.aoa_to_sheet(aoa) : XLSX.utils.aoa_to_sheet([[EMPTY_ROW]]);
  XLSX.utils.book_append_sheet(wb, ws, name.slice(0, 31));
}

/**
 * Construye el workbook Excel del dashboard (sin persistir archivo).
 * Útil para tests y para `exportDashboardToExcel`.
 */
export function buildDashboardWorkbook(data: DashboardExportPayload): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  const resumenRows: Record<string, string | number>[] = [
    { Indicador: "Período", Valor: data.meta.periodoLabel },
    { Indicador: "Distrito", Valor: data.meta.distritoLabel },
    { Indicador: "Inspector", Valor: data.meta.inspectorLabel },
    { Indicador: "", Valor: "" },
    ...data.resumenKpis.map((k) => ({ Indicador: k.title, Valor: k.value })),
  ];
  appendSheet(wb, "Resumen KPIs", resumenRows);

  const actas = data.actasPorTipo;
  appendSheet(
    wb,
    "Actas por tipo",
    actas
      ? [
          { Tipo: "Inspección", Cantidad: actas.inspeccion },
          { Tipo: "Notificación", Cantidad: actas.notificacion },
          { Tipo: "Comprobación", Cantidad: actas.comprobacion },
          { Tipo: "Clausura", Cantidad: actas.clausura },
          { Tipo: "Decomiso", Cantidad: actas.decomiso },
        ]
      : []
  );

  appendSheet(
    wb,
    "Pendientes por distrito",
    data.pendientesDistritos.map((row) => ({
      Distrito: row.distrito_nombre,
      Código: row.distrito_codigo,
      Total: row.total,
      Relevamientos: row.relevamientos,
      "Reins. oficio": row.reinspecciones_oficio,
      "Reins. notificación": row.reinspecciones_notificacion,
    }))
  );

  const riesgoAoa: (string | number)[][] = [];
  const pushBlock = (title: string, headers: string[], rows: (string | number)[][]) => {
    if (riesgoAoa.length > 0) riesgoAoa.push([]);
    riesgoAoa.push([title]);
    riesgoAoa.push(headers);
    if (rows.length === 0) {
      riesgoAoa.push([EMPTY_ROW]);
    } else {
      rows.forEach((r) => riesgoAoa.push(r));
    }
  };

  if (data.riesgo) {
    pushBlock(
      "Top rubros intervenidos",
      ["Rubro", "Cantidad"],
      data.riesgo.top_rubros.map((r) => [r.rubro, r.cantidad])
    );
    pushBlock(
      "Motivos de notificación",
      ["Motivo", "Cantidad"],
      data.riesgo.top_motivos_notificacion.map((m) => [m.motivo, m.cantidad])
    );
    pushBlock(
      "Motivos de comprobación",
      ["Motivo", "Cantidad"],
      data.riesgo.top_motivos_comprobacion.map((m) => [m.motivo, m.cantidad])
    );
    pushBlock(
      "Decomiso kg por rubro",
      ["Rubro", "Kg"],
      data.riesgo.decomiso_kg_por_rubro.map((r) => [r.rubro, r.kg])
    );
    if (data.mercaderiaDecomisadaKg != null) {
      pushBlock("Mercadería decomisada total", ["Kg total"], [[data.mercaderiaDecomisadaKg]]);
    }
  }
  appendAoaSheet(wb, "Riesgo", data.riesgo ? riesgoAoa : []);

  const noRealAoa: (string | number)[][] = [];
  if (data.noRealizadas) {
    const resumen = buildContraproducenciasResumen(data.noRealizadas);
    noRealAoa.push(["Resumen"]);
    noRealAoa.push(["No realizadas total", data.noRealizadasTotal ?? resumen.total]);
    noRealAoa.push([]);
    noRealAoa.push(["Principales contraproducencias"]);
    noRealAoa.push(["Contraproducencia", "Cantidad", "%"]);
    const resumenRows =
      resumen.rows.length > 0
        ? resumen.rows
        : (data.noRealizadas.contraproducencias_resumen ?? []).map((r) => ({
            contraproducencia: r.label,
            cantidad: r.cantidad,
            porcentaje: resumen.total > 0 ? (r.cantidad / resumen.total) * 100 : 0,
          }));
    if (resumenRows.length === 0) {
      noRealAoa.push([EMPTY_ROW]);
    } else {
      resumenRows.forEach((r) => {
        noRealAoa.push([
          r.contraproducencia,
          r.cantidad,
          formatPorcentajeNoRealizadas(
            "porcentaje" in r ? Number(r.porcentaje) : 0
          ),
        ]);
      });
    }
    noRealAoa.push([]);
    noRealAoa.push(["Distritos con más no realizadas"]);
    noRealAoa.push(["Distrito", "Cantidad"]);
    if (data.noRealizadas.distritos_con_mas_no_realizadas.length === 0) {
      noRealAoa.push([EMPTY_ROW]);
    } else {
      data.noRealizadas.distritos_con_mas_no_realizadas.forEach((d) => {
        noRealAoa.push([d.distrito_nombre, d.cantidad]);
      });
    }
  }
  appendAoaSheet(wb, "No realizadas", noRealAoa);

  const prodAoa: (string | number)[][] = [];
  const pushProdTable = (
    title: string,
    headers: string[],
    rows: (string | number)[][]
  ) => {
    if (prodAoa.length > 0) prodAoa.push([]);
    prodAoa.push([title]);
    prodAoa.push(headers);
    if (rows.length === 0) {
      prodAoa.push([EMPTY_ROW]);
    } else {
      rows.forEach((r) => prodAoa.push(r));
    }
  };

  if (data.productividad) {
    pushProdTable(
      "Actuaciones realizadas por inspector",
      [
        "Inspector",
        "Total",
        "Inspecciones",
        "Reins. oficio",
        "Reins. notificación",
        "Otras",
      ],
      data.productividad.inspectores_realizadas.map((r) => [
        r.inspector,
        r.total_realizadas,
        r.inspecciones,
        r.reinspecciones_oficio,
        r.reinspecciones_notificacion,
        r.otras ?? 0,
      ])
    );
    pushProdTable(
      "Actuaciones no realizadas por inspector",
      [
        "Inspector",
        "Total",
        "Local cerrado",
        "No existe",
        "No se ratificó",
        "Clima",
        "Otras",
      ],
      data.productividad.inspectores_no_realizadas.map((r) => [
        r.inspector,
        r.total_no_realizadas,
        r.local_cerrado ?? 0,
        r.no_existe ?? 0,
        r.no_se_ratifico ?? 0,
        r.clima ?? 0,
        r.otras ?? 0,
      ])
    );
    pushProdTable(
      "Actas labradas por inspector",
      ["Inspector", "Notificación", "Comprobación", "Clausura", "Decomiso", "Total actas"],
      data.productividad.actas_por_inspector.map((r) => [
        r.inspector,
        r.notificacion,
        r.comprobacion,
        r.clausura,
        r.decomiso,
        r.total_actas,
      ])
    );
  }
  appendAoaSheet(wb, "Productividad", prodAoa);

  return wb;
}

/** @deprecated Usar `DashboardExportPayload` vía `buildDashboardExportPayload`. */
export type DashboardExportData = DashboardExportPayload;

/**
 * Exporta el dashboard a Excel con hojas alineadas a la pantalla visible.
 */
export function exportDashboardToExcel(data: DashboardExportPayload): void {
  const wb = buildDashboardWorkbook(data);
  const wbout = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  saveAs(new Blob([wbout], { type: "application/octet-stream" }), "indicadores-dashboard.xlsx");
}

export function listDashboardWorkbookSheetNames(data: DashboardExportPayload): string[] {
  return buildDashboardWorkbook(data).SheetNames;
}
