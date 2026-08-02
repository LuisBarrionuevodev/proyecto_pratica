import type { ComprobacionExportRow, ComprobacionExportSlice } from "./comprobacionExportTypes";
import { sliceExportLabel } from "./comprobacionExportTypes";
import { motivoExport, parseAnioMes } from "./comprobacionesExportShared";
export type ComprobacionNormalizedExcelRow = Record<string, string | number>;

function cell(value: unknown): string | number {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && !Number.isNaN(value)) return value;
  return String(value).trim();
}

/** Columnas compactas operativas para export Recorrido (DOCS-EXP.3). */
export const RECORRIDO_EXCEL_COLUMNS = [
  "Fecha actuación",
  "Orden de trabajo",
  "Número de comprobación",
  "Estado",
  "Contribuyente",
  "Documento",
  "Domicilio",
  "Rubro",
  "Motivo de comprobación",
  "Expediente de envío",
  "Oficios",
  "Expedientes de oficio",
  "Expedientes de respuesta",
  "Oficios de respuesta",
  "Causa",
  "Juzgados",
  "Estado recorrido",
  "Reinspección / visita",
  "Inspectores",
] as const;

function buildRecorridoCompactExcelRow(row: ComprobacionExportRow): ComprobacionNormalizedExcelRow {
  return {
    "Fecha actuación": cell(row.fechaActuacion),
    "Orden de trabajo": cell(row.ordenTrabajo),
    "Número de comprobación": cell(row.actaComprobacionNum),
    Estado: cell(sliceExportLabel("recorrido")),
    Contribuyente: cell(row.contribuyente),
    Documento: cell(row.documento),
    Domicilio: cell(row.domicilio),
    Rubro: cell(row.rubro),
    "Motivo de comprobación": cell(motivoExport(row)),
    "Expediente de envío": cell(row.expedienteEnvioCompacto),
    Oficios: cell(row.oficiosNumeros),
    "Expedientes de oficio": cell(row.expedientesOficio),
    "Expedientes de respuesta": cell(row.expedientesRespuesta),
    "Oficios de respuesta": cell(row.oficiosConRespuesta),
    Causa: cell(row.causasAgregadas),
    Juzgados: cell(row.juzgadosAgregados),
    "Estado recorrido": cell(row.estadoRecorridoVisitas || row.estadoRecorrido),
    "Reinspección / visita": cell(row.reinspeccionEstado),
    Inspectores: cell(row.inspectores),
  };
}

/**
 * Filas normalizadas para Excel de actas de comprobación.
 */
export function buildComprobacionesNormalizedExcelRows(
  items: ComprobacionExportRow[],
  slice: ComprobacionExportSlice
): ComprobacionNormalizedExcelRow[] {
  if (slice === "recorrido") {
    return items.map(buildRecorridoCompactExcelRow);
  }

  const sliceLabel = sliceExportLabel(slice);

  return items.map((row) => {
    const { anio, mes } = parseAnioMes(row.fechaActuacion);

    return {
      "Fecha actuación": cell(row.fechaActuacion),
      Año: anio,
      Mes: mes,
      "Orden de trabajo": cell(row.ordenTrabajo),
      "Número de comprobación": cell(row.actaComprobacionNum),
      "Estado / slice": sliceLabel,
      Contribuyente: cell(row.contribuyente),
      Documento: cell(row.documento),
      Domicilio: cell(row.domicilio),
      Calle: cell(row.calle),
      Número: cell(row.numero),
      Rubro: cell(row.rubro),
      "Motivo de comprobación": cell(motivoExport(row)),
      "Expediente de envío número": cell(row.expedienteEnvioNumero),
      "Expediente de envío año": cell(row.expedienteEnvioAnio),
      "Fecha expediente de envío": cell(row.fechaExpedienteEnvio),
      "Oficio número": cell(row.oficioNumero),
      "Oficio año": cell(row.oficioAnio),
      "Fecha oficio": cell(row.fechaOficio),
      Causa: cell(row.causa),
      Juzgado: cell(row.juzgado),
      "Expediente de respuesta número": cell(row.expedienteRespuestaNumero),
      "Expediente de respuesta año": cell(row.expedienteRespuestaAnio),
      "Fecha expediente de respuesta": cell(row.fechaExpedienteRespuesta),
      "Estado oficio / cumplimiento": cell(row.resultadoCumplimiento || row.estadoRecorrido),
      "Reinspección / visita": cell(row.reinspeccionEstado),
      Inspectores: cell(row.inspectores),
      "Actuación ID": cell(row.actuacionId),
      "Comprobación ID": cell(row.comprobacionId ?? ""),
    };
  });
}
