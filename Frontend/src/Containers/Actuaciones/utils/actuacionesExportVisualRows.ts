import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  actuacionActaChipsOnly,
  actuacionActasYTramiteAccessor,
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

function motivosInfraccionSegments(row: IActuacionListItem): string[] {
  const out: string[] = [];
  const comp = (row.comprobacion_motivo ?? "").trim();
  if (comp) out.push(`Motivo comprobación: ${comp}`);
  const mf = [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  if (mf.length === 1) out.push(`Motivo notificación: ${mf[0]}`);
  else if (mf.length > 1) out.push(`Motivos notificación: ${mf.join(", ")}`);
  return out;
}

function fechaOtText(row: IActuacionListItem): string {
  const fecha = (row.fecha_actuacion ?? "").trim() || "—";
  const ot = (row.orden_trabajo_numero ?? "").trim();
  return ot ? `${fecha} · OT ${ot}` : fecha;
}

function tipoContraproducenciaText(row: IActuacionListItem): string {
  const tipo = (row.tipo_actuacion ?? "").trim();
  const contra = (row.contraproducencia ?? "").trim();
  const parts = [
    tipo ? `Tipo: ${tipo}` : "",
    contra ? `Contraproducencia: ${contra}` : "",
  ].filter(Boolean);
  return parts.join(" · ") || "—";
}

function domicilioRubroText(row: IActuacionListItem): string {
  const line = formatActuacionListDomicilioLinea(row).trim() || "—";
  const rubro = (row.rubro_nombre ?? "").trim();
  return rubro ? `${line} · ${rubro}` : line;
}

function actasTramiteText(row: IActuacionListItem): string {
  const labels = [...actuacionActaChipsOnly(row), ...actuacionDocumentacionTramiteSegments(row)];
  if (!labels.length) return "—";
  return labels.join("\n");
}

/** Filas visuales alineadas a columnas compuestas de la grilla Actuaciones. */
export function buildActuacionesVisualPdfRows(items: IActuacionListItem[]): ActuacionVisualPdfRow[] {
  return items.map((row) => ({
    fechaOt: fechaOtText(row),
    tipoContraproducencia: tipoContraproducenciaText(row),
    domicilioRubro: domicilioRubroText(row),
    inspectores: inspectoresNombres(row).join(", ") || "—",
    actasTramite: actasTramiteText(row),
    motivos: motivosInfraccionSegments(row).join("\n") || "—",
  }));
}

/** Accessor compacto útil para logs / tests. */
export function actuacionVisualSummaryLine(row: IActuacionListItem): string {
  return actuacionActasYTramiteAccessor(row);
}
