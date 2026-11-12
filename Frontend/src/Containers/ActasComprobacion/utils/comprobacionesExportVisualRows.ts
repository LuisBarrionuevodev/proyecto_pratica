import type { ComprobacionExportRow } from "./comprobacionExportTypes";
import { cellStr, motivoExport } from "./comprobacionesExportShared";

export type ComprobacionVisualPdfRow = {
  layout: "operativa" | "recorrido";
  fechaOt: string;
  comprobacion: string;
  domicilioRubro: string;
  contribuyente: string;
  motivo: string;
  expedienteOficio: string;
  estadoReinspeccion: string;
  fechaComprobacion: string;
  titularDocumento: string;
  oficioExpOtMotivos: string;
  tipoConclusion: string;
  seguimientoOtFecha: string;
};

function joinLines(parts: Array<string | null | undefined>): string {
  return parts.map((p) => String(p ?? "").trim()).filter(Boolean).join("\n");
}

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

function titularDocumentoText(row: ComprobacionExportRow): string {
  return joinLines([row.contribuyente, row.documento]) || "—";
}

function fechaComprobacionText(row: ComprobacionExportRow): string {
  const fecha = cellStr(row.fechaActuacion);
  const n = cellStr(row.actaComprobacionNum);
  const envio = cellStr(row.expedienteEnvioCompacto);
  return joinLines([fecha, n ? `Comp. ${n}` : "", envio ? `Exp. envío ${envio}` : ""]);
}

function causaLinea(raw: string | null | undefined): string {
  const c = String(raw ?? "").trim();
  if (!c || c === "—") return "";
  return /^causa\b/i.test(c) ? c : `Causa ${c}`;
}

function oficioExpOtMotivosText(row: ComprobacionExportRow): string {
  const lines: string[] = [];
  const detalles = row.oficiosDetalle ?? [];
  if (detalles.length > 0) {
    for (const d of detalles) {
      const of = d.oficioNumero
        ? d.oficioNumero.toLowerCase().startsWith("oficio")
          ? d.oficioNumero
          : `Oficio ${d.oficioNumero}`
        : "";
      const exp = d.expedienteNumero
        ? d.expedienteNumero.toLowerCase().startsWith("exp")
          ? d.expedienteNumero
          : `Exp. ${d.expedienteNumero}`
        : "";
      if (of) lines.push(of);
      if (exp) lines.push(exp);
    }
  } else if (row.oficiosAgregados || row.expedientesAgregados) {
    if (row.oficiosAgregados) lines.push(row.oficiosAgregados);
    if (row.expedientesAgregados) lines.push(row.expedientesAgregados);
  }
  if (row.ordenTrabajo) lines.push(`OT origen ${row.ordenTrabajo}`);
  if (detalles.length > 0) {
    for (const d of detalles) {
      const causa = causaLinea(d.causa);
      if (causa) lines.push(causa);
    }
  } else {
    const causa = causaLinea(row.causasAgregadas || row.causa);
    if (causa) lines.push(causa);
  }
  const mot = motivoExport(row);
  if (mot) lines.push(mot);
  return lines.join("\n");
}

function tipoConclusionText(row: ComprobacionExportRow): string {
  const detalles = row.oficiosDetalle ?? [];
  if (detalles.length === 0) return "";
  return detalles
    .map((d) =>
      joinLines([
        d.tipoReinspeccion,
        d.conclusion,
        d.actaDecomisoOrigen ? `Acta de decomiso origen: N.º ${d.actaDecomisoOrigen}` : "",
        d.kilosDecomisoOrigen ? `Kilos decomiso origen: ${d.kilosDecomisoOrigen}` : "",
        d.actaClausuraOrigen ? `Acta de clausura origen: N.º ${d.actaClausuraOrigen}` : "",
      ])
    )
    .filter(Boolean)
    .join("\n");
}

function seguimientoOtFechaText(row: ComprobacionExportRow): string {
  const detalles = row.oficiosDetalle ?? [];
  if (detalles.length === 0) return "";
  return detalles
    .map((d) => {
      if (d.seguimiento === "Pendiente de reinspección") return d.seguimiento;
      return joinLines([
        d.seguimiento,
        d.otReinspeccion ? `OT ${d.otReinspeccion}` : "",
        d.fechaReinspeccion ? `Fecha ${d.fechaReinspeccion}` : "",
      ]);
    })
    .filter(Boolean)
    .join("\n");
}

/**
 * Filas compactas para el detalle PDF de comprobaciones.
 */
export function buildComprobacionesVisualPdfRows(items: ComprobacionExportRow[]): ComprobacionVisualPdfRow[] {
  return items.map((row) => {
    const dom = row.domicilio || "—";
    const rubro = cellStr(row.rubro);
    const comp = cellStr(row.actaComprobacionNum);
    const layout = row.exportSlice === "recorrido" ? "recorrido" : "operativa";

    return {
      layout,
      fechaOt: fechaOtText(row),
      comprobacion: comp ? `Comp. ${comp}` : "—",
      domicilioRubro: rubro ? `${dom} · ${rubro}` : dom,
      contribuyente: row.contribuyente || "—",
      motivo: motivoExport(row) || "—",
      expedienteOficio: expedienteOficioText(row),
      estadoReinspeccion: estadoReinspeccionText(row),
      fechaComprobacion: fechaComprobacionText(row) || "—",
      titularDocumento: titularDocumentoText(row),
      oficioExpOtMotivos: oficioExpOtMotivosText(row),
      tipoConclusion: tipoConclusionText(row),
      seguimientoOtFecha: seguimientoOtFechaText(row),
    };
  });
}
