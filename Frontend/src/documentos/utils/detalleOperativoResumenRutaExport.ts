import type { IDetalleOperativoItem, IIniciadorOperativoCampos } from "../../api/rutasTrabajoApi";
import { formatoNumeroConAnio } from "../../Containers/RutasTrabajo/planificacion/utils/iniciadorDisplay";
import { buildDetalleOperativoPdfSegments } from "./detalleOperativoPdfSegments";

const TIPO_NOTIFICACION = "REINSPECCION_NOTIFICACION";

const PRIORIDAD_RE = /^prioridad\b/i;
const VENCIMIENTO_LABEL_RE = /^(vence|vencimiento|plazo|por vencer)\b/i;

function esNotificacion(row: IIniciadorOperativoCampos): boolean {
  return (row.tipo_iniciador ?? "").trim().toUpperCase() === TIPO_NOTIFICACION;
}

function labelDeSegmento(seg: string): string {
  const idx = seg.indexOf(":");
  return (idx >= 0 ? seg.slice(0, idx) : seg).trim();
}

function expedienteProrrogaDesdeValorProrroga(valor: string): string | null {
  const val = valor.trim();
  if (!val) return null;
  const expMatch = /Exp\.?\s*([\d/]+)/i.exec(val);
  if (expMatch?.[1]) return expMatch[1].trim();
  if (/^\d+\s*d[ií]as?$/i.test(val)) return null;
  const numAnio = /(\d[\d/]*\/\d{4})/.exec(val);
  return numAnio?.[1]?.trim() ?? null;
}

function expedienteProrrogaDesdeItems(items: IDetalleOperativoItem[] | undefined): string | null {
  const prorroga = items?.find((i) => /^prórroga$/i.test((i.label ?? "").trim()));
  if (!prorroga?.value) return null;
  return expedienteProrrogaDesdeValorProrroga(prorroga.value);
}

function expedienteProrrogaDesdeRow(row: IIniciadorOperativoCampos): string | null {
  const texto = row.prorroga_texto?.trim() ?? row.identificadores?.prorroga_texto?.trim();
  if (texto) return expedienteProrrogaDesdeValorProrroga(texto);
  return null;
}

function numeroNotificacionExport(row: IIniciadorOperativoCampos): string | null {
  const items = row.detalle_operativo_items;
  const notiItem = items?.find((i) => /^notif\.?$/i.test((i.label ?? "").trim()));
  if (notiItem?.value?.trim()) return notiItem.value.trim();
  return formatoNumeroConAnio(
    row.identificadores?.numero_notificacion,
    row.identificadores?.anio_notificacion
  );
}

function buildNotificacionResumenExportSegments(row: IIniciadorOperativoCampos): string[] {
  const segments: string[] = [];
  const noti = numeroNotificacionExport(row);
  if (noti) segments.push(`Notif. Nº ${noti}`);

  const expProrroga =
    expedienteProrrogaDesdeItems(row.detalle_operativo_items) ?? expedienteProrrogaDesdeRow(row);
  if (expProrroga) segments.push(`Exp. prórroga: ${expProrroga}`);

  return segments;
}

function filtrarSegmentosResumenExport(segments: string[]): string[] {
  return segments.filter((seg) => {
    const trimmed = seg.trim();
    if (!trimmed) return false;
    const label = labelDeSegmento(trimmed);
    if (PRIORIDAD_RE.test(label) || PRIORIDAD_RE.test(trimmed)) return false;
    if (VENCIMIENTO_LABEL_RE.test(label)) return false;
    if (/^prórroga:/i.test(trimmed) && /\d+\s*d[ií]as?/i.test(trimmed)) return false;
    return true;
  });
}

/**
 * Segmentos de detalle operativo para el PDF «Resumen de ruta» (sin prioridad ni vencimiento de notificación).
 */
export function buildDetalleOperativoResumenRutaExport(row: IIniciadorOperativoCampos): string[] {
  if (esNotificacion(row)) {
    return buildNotificacionResumenExportSegments(row);
  }
  return filtrarSegmentosResumenExport(buildDetalleOperativoPdfSegments(row));
}
