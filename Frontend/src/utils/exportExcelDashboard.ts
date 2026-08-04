import * as XLSX from "xlsx";
import { saveAs } from "file-saver";

import type { DashboardExportPayload } from "../Containers/Dashboard/utils/buildDashboardExportPayload";

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
      Relevamientos: row.relevamientos,
      Denuncias: row.denuncias,
      "Reins. oficio": row.reinspecciones_oficio,
      "Reins. notificación": row.reinspecciones_notificacion,
      "Sin geolocalización": row.sin_geolocalizacion,
      Total: row.total,
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
    const pt = data.noRealizadas.por_tipo;
    noRealAoa.push(["Resumen por tipo"]);
    noRealAoa.push(["Tipo", "Cantidad"]);
    noRealAoa.push(["Total", data.noRealizadasTotal ?? 0]);
    noRealAoa.push(["Inspección", pt.inspeccion]);
    noRealAoa.push(["Reinspección oficio", pt.reinspeccion_oficio]);
    noRealAoa.push(["Reinspección notificación", pt.reinspeccion_notificacion]);
    noRealAoa.push(["Denuncia", pt.denuncia]);
    noRealAoa.push([]);
    noRealAoa.push(["Top contraproducencias"]);
    noRealAoa.push(["Contraproducencia", "Cantidad"]);
    if (data.noRealizadas.top_contraproducencias.length === 0) {
      noRealAoa.push([EMPTY_ROW]);
    } else {
      data.noRealizadas.top_contraproducencias.forEach((r) => {
        noRealAoa.push([r.contraproducencia, r.cantidad]);
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
        "Denuncias",
        "Tipo principal",
      ],
      data.productividad.inspectores_realizadas.map((r) => [
        r.inspector,
        r.total_realizadas,
        r.inspecciones,
        r.reinspecciones_oficio,
        r.reinspecciones_notificacion,
        r.denuncias,
        r.tipo_principal,
      ])
    );
    pushProdTable(
      "Actuaciones no realizadas por inspector",
      [
        "Inspector",
        "Total",
        "Contraproducencia principal",
        "Inspecciones",
        "Reins. oficio",
        "Reins. notificación",
        "Denuncias",
      ],
      data.productividad.inspectores_no_realizadas.map((r) => [
        r.inspector,
        r.total_no_realizadas,
        r.contraproducencia_principal,
        r.inspecciones,
        r.reinspecciones_oficio,
        r.reinspecciones_notificacion,
        r.denuncias,
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
