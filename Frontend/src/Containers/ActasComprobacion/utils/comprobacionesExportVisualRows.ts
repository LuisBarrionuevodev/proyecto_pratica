import type { ComprobacionExportRow } from "./comprobacionExportTypes";
import { cellStr, motivoExport } from "./comprobacionesExportShared";

export type ComprobacionVisualPdfRow = {
  fechaOt: string;
  comprobacion: string;
  domicilioRubro: string;
  contribuyente: string;
  motivo: string;
  expedienteOficio: string;
  estadoReinspeccion: string;
};

function fechaOtText(row: ComprobacionExportRow): string {
  const fecha = row.fechaActuacion || "—";
  const ot = row.ordenTrabajo;
  return ot ? `${fecha} · OT ${ot}` : fecha;
}

function expedienteOficioText(row: ComprobacionExportRow): string {
  if (row.exportSlice === "recorrido" && (row.oficiosAgregados || row.expedientesAgregados)) {
    const segs = [row.oficiosAgregados, row.expedientesAgregados].filter(Boolean);
    if (row.juzgado) segs.push(row.juzgado);
    return segs.join("\n") || "—";
  }
  const segs: string[] = [];
  if (row.expedienteEnvioNumero || row.expedienteEnvioAnio) {
    segs.push(`Exp. envío ${[row.expedienteEnvioNumero, row.expedienteEnvioAnio].filter(Boolean).join("/")}`);
  }
  if (row.oficioNumero || row.oficioAnio) {
    segs.push(`Oficio ${[row.oficioNumero, row.oficioAnio].filter(Boolean).join("/")}`);
  }
  if (row.expedienteRespuestaNumero || row.expedienteRespuestaAnio) {
    segs.push(`Exp. resp. ${[row.expedienteRespuestaNumero, row.expedienteRespuestaAnio].filter(Boolean).join("/")}`);
  }
  if (row.juzgado) segs.push(row.juzgado);
  return segs.join("\n") || "—";
}

function estadoReinspeccionText(row: ComprobacionExportRow): string {
  if (row.exportSlice === "recorrido" && row.estadoRecorridoVisitas) {
    const segs = [row.estadoRecorridoVisitas];
    if (row.reinspeccionEstado) segs.push(row.reinspeccionEstado);
    return segs.join("\n");
  }
  const segs: string[] = [];
  if (row.estadoRecorrido) segs.push(row.estadoRecorrido);
  if (row.resultadoCumplimiento) segs.push(`Cumplimiento: ${row.resultadoCumplimiento}`);
  if (row.reinspeccionEstado) segs.push(row.reinspeccionEstado);
  return segs.join("\n") || "—";
}

/**
 * Filas compactas para el detalle PDF de comprobaciones.
 */
export function buildComprobacionesVisualPdfRows(items: ComprobacionExportRow[]): ComprobacionVisualPdfRow[] {
  return items.map((row) => {
    const dom = row.domicilio || "—";
    const rubro = cellStr(row.rubro);
    const comp = cellStr(row.actaComprobacionNum);

    return {
      fechaOt: fechaOtText(row),
      comprobacion: comp ? `Comp. ${comp}` : "—",
      domicilioRubro: rubro ? `${dom} · ${rubro}` : dom,
      contribuyente: row.contribuyente || "—",
      motivo: motivoExport(row) || "—",
      expedienteOficio: expedienteOficioText(row),
      estadoReinspeccion: estadoReinspeccionText(row),
    };
  });
}
