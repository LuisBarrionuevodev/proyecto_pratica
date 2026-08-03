import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { contribuyenteBandejaLabel } from "../../../utils/contribuyenteBandejaText";
import { domicilioLineaOperativo } from "../../../utils/formatDomicilioLineaVisible";
import { sliceLabel, type PlazoOperativoSlice } from "../gestionNotificacionPlazo";

export function normalizeMotivoKey(val: unknown): string {
  return String(val ?? "")
    .trim()
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ");
}

export function motivosNotificacionList(row: IActuacionesPendientesItem): string[] {
  return [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
}

export function motivosNotificacionConcat(row: IActuacionesPendientesItem): string {
  const parts = motivosNotificacionList(row);
  return parts.length ? parts.join("; ") : "";
}

export function domicilioLinea(row: IActuacionesPendientesItem): string {
  return domicilioLineaOperativo(row);
}

export function inspectoresTexto(row: IActuacionesPendientesItem): string {
  const texto = row.inspectores_texto?.trim();
  if (texto) return texto;
  const fromArr = row.inspectores?.filter((s): s is string => Boolean(s?.trim()));
  if (fromArr?.length) return fromArr.map((s) => s.trim()).join(", ");
  return [row.inspector1, row.inspector2, row.inspector3].filter((s): s is string => Boolean(s?.trim())).join(", ");
}

export function fechaVencimientoRow(row: IActuacionesPendientesItem): string {
  return (row.documentacion_contexto?.propia?.notificacion_fecha_vencimiento ?? "").trim();
}

export function plazoInicialDias(row: IActuacionesPendientesItem): number | null {
  const p = row.documentacion_contexto?.propia?.notificacion_plazo_dias;
  if (p == null) return null;
  const n = Number(p);
  return Number.isFinite(n) ? n : null;
}

export function parseAnioMes(fecha: string | null | undefined): { anio: string; mes: string } {
  const f = (fecha ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(f)) return { anio: "", mes: "" };
  const [y, m] = f.slice(0, 10).split("-");
  return { anio: y, mes: m };
}

export function estadoPlazoText(row: IActuacionesPendientesItem): string {
  const d = row.dias_restantes;
  if (d === null || d === undefined) return "";
  if (d === 0) return "Vencida o hoy";
  if (d >= 5) return "En plazo";
  if (d >= 1) return "Por vencer";
  return "";
}

export function diasRestantesText(row: IActuacionesPendientesItem): string {
  const d = row.dias_restantes;
  if (d === null || d === undefined) return "";
  if (d === 1) return "1 día";
  return `${d} días`;
}

export function sliceExportLabel(slice: PlazoOperativoSlice): string {
  return slice === "total" ? "Historial" : sliceLabel(slice);
}

export function contribuyenteExport(row: IActuacionesPendientesItem): string {
  return contribuyenteBandejaLabel(row.contrib_apellido, row.contrib_nombre, row.razon_social);
}

export function tieneComprobacionPosterior(row: IActuacionesPendientesItem): boolean {
  return Boolean(String(row.comprobacion_posterior_acta_num ?? "").trim());
}

export function anioDesdeFechaActuacion(fecha: string | null | undefined): string {
  const f = (fecha ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(f)) return "";
  return f.slice(0, 4);
}

/** Formato compacto `número/año` para actas de notificación en export. */
export function formatNotificacionActaNumAnio(
  numero: string | null | undefined,
  anio: string | number | null | undefined
): string {
  const n = (numero ?? "").trim();
  if (!n) return "";
  const a = anio != null ? String(anio).trim() : "";
  return a ? `${n}/${a}` : n;
}

/** Acta de notificación origen (reinspección); solo lectura del row/API. */
export function notificacionOrigenActaText(row: IActuacionesPendientesItem): string {
  const on = row.origen_reinspeccion_notificacion;
  if (on?.notificacion_acta_numero?.trim()) {
    return formatNotificacionActaNumAnio(on.notificacion_acta_numero, on.notificacion_acta_anio);
  }
  const texto = (row as { notificacion_origen_texto?: string | null }).notificacion_origen_texto?.trim();
  return texto ?? "";
}

/** Acta de notificación propia de la fila (visita actual). */
export function actaNotificacionPropiaText(row: IActuacionesPendientesItem): string {
  const num = (row.acta_notificacion_num ?? "").trim();
  if (!num) return "";
  return formatNotificacionActaNumAnio(num, anioDesdeFechaActuacion(row.fecha_actuacion));
}

/** Fila de reinspección por notificación (circuito documental o tipo REINSPECCION con origen). */
export function esFilaReinspeccionPorNotificacion(row: IActuacionesPendientesItem): boolean {
  if (row.documentacion_contexto?.circuito === "REINSPECCION_NOTIFICACION") return true;
  if (String(row.tipo_actuacion ?? "").toUpperCase() === "REINSPECCION" && notificacionOrigenActaText(row)) {
    return true;
  }
  return false;
}

/**
 * Columna «Notificación» del PDF: diferencia origen de reinspección y acta propia.
 * Solo presentación; no altera datos operativos.
 */
export function notificacionExportPdfText(row: IActuacionesPendientesItem): string {
  const origenTxt = notificacionOrigenActaText(row);
  const propiaTxt = actaNotificacionPropiaText(row);
  const esRein = esFilaReinspeccionPorNotificacion(row);

  if (esRein && origenTxt) {
    const lineas = [`Notif. origen: ${origenTxt}`];
    if (propiaTxt && propiaTxt !== origenTxt) {
      lineas.push(`Acta notif.: ${propiaTxt}`);
    }
    return lineas.join("\n");
  }

  if (propiaTxt) return `Notif. ${propiaTxt}`;
  return "—";
}
