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
