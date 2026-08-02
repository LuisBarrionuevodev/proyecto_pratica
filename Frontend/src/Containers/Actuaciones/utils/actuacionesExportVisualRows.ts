import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { domicilioLineaOperativo } from "../../../utils/formatDomicilioLineaVisible";
import {
  actuacionActaChipsOnly,
  actuacionDocumentacionOrigenReinspeccionSegments,
  actuacionDocumentacionPropiaTramiteSegments,
  actuacionDocumentacionTramiteSegments,
} from "./actuacionDocumentacionVisual";
import { splitCommaList } from "../Components/bandejaTableCells";

export type ActuacionVisualPdfRow = {
  fechaOt: string;
  tipoContraproducencia: string;
  domicilioRubro: string;
  inspectores: string;
  actasTramite: string;
  motivos: string;
};

function inspectoresNombres(row: IActuacionListItem): string[] {
  const fromArr = row.inspectores?.filter((s): s is string => Boolean(s?.trim()));
  if (fromArr && fromArr.length > 0) return fromArr.map((s) => s.trim());
  const texto = row.inspectores_texto?.trim();
  if (texto) return splitCommaList(texto);
  return [row.inspector1, row.inspector2, row.inspector3].filter((s): s is string => Boolean(s?.trim()));
}

function tieneNotifMotivosReales(row: IActuacionListItem): boolean {
  return [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3].some((s) =>
    Boolean((s ?? "").trim())
  );
}

/** Motivos de actas labradas en la visita (no previas sin acta ni comprobación PENDIENTE). */
function motivosPdfDisplay(row: IActuacionListItem): string {
  const out: string[] = [];
  const compLabrada =
    Boolean(row.acta_comprobacion_num?.trim()) &&
    (row.comprobacion_motivo ?? "").trim() &&
    (row.comprobacion_motivo ?? "").trim() !== "PENDIENTE";
  if (compLabrada) {
    out.push(`Motivo comprobación: ${(row.comprobacion_motivo ?? "").trim()}`);
  }
  const notifLabrada = Boolean(row.acta_notificacion_num?.trim()) && tieneNotifMotivosReales(row);
  if (notifLabrada) {
    const mf = [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
      .map((s) => (s ?? "").trim())
      .filter(Boolean);
    if (mf.length === 1) out.push(`Motivo notificación: ${mf[0]}`);
    else if (mf.length > 1) out.push(`Motivos notificación: ${mf.join(", ")}`);
  }
  return out.length ? out.join("\n") : "—";
}

function fechaOtText(row: IActuacionListItem): string {
  const fecha = (row.fecha_actuacion ?? "").trim() || "—";
  const ot = (row.orden_trabajo_numero ?? "").trim();
  return ot ? `${fecha} · OT ${ot}` : fecha;
}

/** Tipo, contraproducencia y segmentos de origen de reinspección (referencia contextual en columna tipo). */
function tipoTramiteConOrigenText(row: IActuacionListItem): string {
  const tipo = (row.tipo_actuacion ?? "").trim();
  const contra = (row.contraproducencia ?? "").trim();
  const baseParts = [
    tipo ? `Tipo: ${tipo}` : "",
    contra ? `Contraproducencia: ${contra}` : "",
  ].filter(Boolean);
  const origenSegs = actuacionDocumentacionOrigenReinspeccionSegments(row);
  const lines = [...baseParts, ...origenSegs];
  return lines.length ? lines.join("\n") : "—";
}

function domicilioRubroText(row: IActuacionListItem): string {
  const line = domicilioLineaOperativo(row).trim() || "—";
  const rubro = (row.rubro_nombre ?? "").trim();
  return rubro ? `${line} · ${rubro}` : line;
}

/** Actas y trámite propio de la visita (sin bloque de origen documental de reinspección). */
function actasTramiteSoloPropias(row: IActuacionListItem): string {
  const labels = [...actuacionActaChipsOnly(row), ...actuacionDocumentacionPropiaTramiteSegments(row)];
  if (!labels.length) return "—";
  return labels.join("\n");
}

/** Filas visuales alineadas a columnas compuestas de la grilla Actuaciones. */
export function buildActuacionesVisualPdfRows(items: IActuacionListItem[]): ActuacionVisualPdfRow[] {
  return items.map((row) => ({
    fechaOt: fechaOtText(row),
    tipoContraproducencia: tipoTramiteConOrigenText(row),
    domicilioRubro: domicilioRubroText(row),
    inspectores: inspectoresNombres(row).join(", ") || "—",
    actasTramite: actasTramiteSoloPropias(row),
    motivos: motivosPdfDisplay(row),
  }));
}

/** Accessor compacto útil para logs / tests. */
export function actuacionVisualSummaryLine(row: IActuacionListItem): string {
  return [...actuacionActaChipsOnly(row), ...actuacionDocumentacionTramiteSegments(row)].join(" | ");
}
