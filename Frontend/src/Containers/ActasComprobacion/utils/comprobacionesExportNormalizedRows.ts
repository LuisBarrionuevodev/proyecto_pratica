import type { ComprobacionExportRow, ComprobacionExportSlice, RecorridoOficioExportDetalle } from "./comprobacionExportTypes";
import { sliceExportLabel } from "./comprobacionExportTypes";
import { motivoExport, parseAnioMes } from "./comprobacionesExportShared";
export type ComprobacionNormalizedExcelRow = Record<string, string | number>;

function cell(value: unknown): string | number {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && !Number.isNaN(value)) return value;
  return String(value).trim();
}

/** Columnas atómicas Recorrido: una fila Excel por oficio. */
export const RECORRIDO_EXCEL_COLUMNS = [
  "Fecha comprobación",
  "N.º comprobación",
  "Expediente de envío",
  "Titular o razón social",
  "Documento",
  "Domicilio",
  "Rubro",
  "N.º oficio",
  "N.º expediente",
  "OT origen",
  "Causa",
  "Motivos de comprobación",
  "Tipo de reinspección",
  "Conclusión de reinspección",
  "Seguimiento",
  "OT reinspección",
  "Fecha de reinspección",
  "Acta decomiso origen",
  "Kilos decomiso origen",
  "Acta clausura origen",
] as const;

export const RECORRIDO_EXCEL_COL_WIDTHS = [
  14, 16, 16, 28, 14, 28, 16, 14, 16, 12, 14, 28, 22, 18, 24, 14, 16, 18, 16, 18,
];

const EMPTY_OFICIO_DETALLE: RecorridoOficioExportDetalle = {
  oficioNumero: "",
  expedienteNumero: "",
  causa: "",
  tipoReinspeccion: "",
  conclusion: "",
  seguimiento: "",
  otReinspeccion: "",
  fechaReinspeccion: "",
  actaDecomisoOrigen: "",
  kilosDecomisoOrigen: "",
  actaClausuraOrigen: "",
};

function buildRecorridoOficioExcelRow(
  row: ComprobacionExportRow,
  detalle: RecorridoOficioExportDetalle
): ComprobacionNormalizedExcelRow {
  return {
    "Fecha comprobación": cell(row.fechaActuacion),
    "N.º comprobación": cell(row.actaComprobacionNum),
    "Expediente de envío": cell(row.expedienteEnvioCompacto),
    "Titular o razón social": cell(row.contribuyente),
    Documento: cell(row.documento),
    Domicilio: cell(row.domicilio),
    Rubro: cell(row.rubro),
    "N.º oficio": cell(detalle.oficioNumero),
    "N.º expediente": cell(detalle.expedienteNumero),
    "OT origen": cell(row.ordenTrabajo),
    Causa: cell(
      detalle.causa ||
        ((row.oficiosDetalle?.length ?? 0) > 1 ? "" : row.causasAgregadas || row.causa)
    ),
    "Motivos de comprobación": cell(motivoExport(row)),
    "Tipo de reinspección": cell(detalle.tipoReinspeccion),
    "Conclusión de reinspección": cell(detalle.conclusion),
    Seguimiento: cell(detalle.seguimiento),
    "OT reinspección": cell(detalle.otReinspeccion),
    "Fecha de reinspección": cell(detalle.fechaReinspeccion),
    "Acta decomiso origen": cell(detalle.actaDecomisoOrigen),
    "Kilos decomiso origen": cell(detalle.kilosDecomisoOrigen),
    "Acta clausura origen": cell(detalle.actaClausuraOrigen),
  };
}

function buildRecorridoExcelRows(row: ComprobacionExportRow): ComprobacionNormalizedExcelRow[] {
  const detalles =
    row.oficiosDetalle && row.oficiosDetalle.length > 0 ? row.oficiosDetalle : [EMPTY_OFICIO_DETALLE];
  return detalles.map((detalle) => buildRecorridoOficioExcelRow(row, detalle));
}

/**
 * Filas normalizadas para Excel de actas de comprobación.
 */
export function buildComprobacionesNormalizedExcelRows(
  items: ComprobacionExportRow[],
  slice: ComprobacionExportSlice
): ComprobacionNormalizedExcelRow[] {
  if (slice === "recorrido") {
    return items.flatMap(buildRecorridoExcelRows);
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
