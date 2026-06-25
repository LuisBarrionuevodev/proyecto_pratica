/**
 * Bloque INSPECCIONES BROMATOLÓGICAS del PDF de exportación Actuaciones.
 *
 * Calcula desde las filas exportadas (`IActuacionListItem[]`) usando la misma semántica
 * orientativa que D1c / `_count_actas_labradas` en backend:
 * - actas solo si son propias de la visita labrada en el listado exportado (no solo referencia previa);
 * - notificación: cuenta con acta visible y motivos reales cargados en el presenter de fila;
 * - comprobación: acta visible y motivo no vacío ni `PENDIENTE`;
 * - kilos: suma desde `decomiso_kilos_total` solo cuando hay acta de decomiso propia en la fila.
 */
import type { IActuacionListItem } from "../../../api/actuacionesListApi";

export type ActuacionPdfResumenPair = {
  indicator: string;
  value: string;
};

/** Normalización para coincidencias con catálogo / backend (mayúsculas, espacio único). */
export function normalizeTipoExport(val: unknown): string {
  return String(val ?? "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, " ");
}

/** Tipo sin acentos, guiones bajos → espacio (ratificaciones, variantes de catálogo). */
export function normalizeTipoRatificacion(val: unknown): string {
  return normalizeTipoExport(val)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/_/g, " ");
}

/** Inspección de campo inicial (integral, etc.) sin confundir con reinspección. */
export function isInspeccionIntegralOrDenuncia(row: IActuacionListItem): boolean {
  const u = normalizeTipoExport(row.tipo_actuacion);
  if (!u) return false;
  if (u.includes("DENUNCIA")) return true;
  if (u.includes("REINSPECCION")) return false;
  if (u === "INSPECCION") return true;
  if (u.includes("INSPECCION")) return true;
  return false;
}

function origenReinspeccionNotificacionPresente(row: IActuacionListItem): boolean {
  const on = row.origen_reinspeccion_notificacion;
  return Boolean(
    on &&
      (on.notificacion_acta_numero?.trim() ||
        on.expediente_numero != null ||
        on.fecha_vencimiento?.trim() ||
        on.plazo_dias != null ||
        (on.prorroga_dias != null && on.prorroga_dias > 0))
  );
}

function origenReinspeccionOficioPresente(row: IActuacionListItem): boolean {
  const oo = row.origen_reinspeccion_oficio;
  return Boolean(
    oo &&
      (oo.comprobacion_acta_numero?.trim() ||
        oo.oficio_numero != null ||
        oo.expediente_numero != null ||
        oo.oficio_causa?.trim())
  );
}

/** Actuación de reinspección por notificación (visita del período, no acta previa de origen). */
export function isReinspeccionPorNotificacion(row: IActuacionListItem): boolean {
  if (row.documentacion_contexto?.circuito === "REINSPECCION_NOTIFICACION") return true;
  if (origenReinspeccionNotificacionPresente(row)) return true;
  const u = normalizeTipoExport(row.tipo_actuacion);
  return Boolean(u.includes("REINSPECCION") && u.includes("NOTIFICACION"));
}

/**
 * Actuación de reinspección por oficio.
 * Excluye las ya clasificadas como reinspección por notificación.
 * Incluye tipo genérico `REINSPECCION` con origen/circuito de oficio (caso operativo habitual).
 */
export function isReinspeccionPorOficio(row: IActuacionListItem): boolean {
  if (isReinspeccionPorNotificacion(row)) return false;
  if (row.documentacion_contexto?.circuito === "REINSPECCION_OFICIO") return true;
  if (origenReinspeccionOficioPresente(row)) return true;
  const u = normalizeTipoExport(row.tipo_actuacion);
  if (u.includes("REINSPECCION") && u.includes("OFICIO")) return true;
  if (u === "REINSPECCION") return true;
  return false;
}

/** Ratificación de clausura (tipo de visita, no acta de clausura labrada). */
export function isRatificacionClausura(row: IActuacionListItem): boolean {
  const u = normalizeTipoRatificacion(row.tipo_actuacion);
  if (!u.includes("RATIFICACION")) return false;
  return u.includes("CLAUSURA");
}

/** Ratificación de decomiso (tipo de visita, no acta de decomiso labrada). */
export function isRatificacionDecomiso(row: IActuacionListItem): boolean {
  const u = normalizeTipoRatificacion(row.tipo_actuacion);
  if (!u.includes("RATIFICACION")) return false;
  return u.includes("DECOMISO");
}

/** Visita «Verificar e informar» (oficio / seguimiento administrativo). */
export function isVerificarEInformar(row: IActuacionListItem): boolean {
  const u = normalizeTipoRatificacion(row.tipo_actuacion);
  return u.includes("VERIFICAR") && u.includes("INFORMAR");
}

export function tieneNotificacionLabradaMotivos(row: IActuacionListItem): boolean {
  const num = row.acta_notificacion_num?.trim();
  if (!num) return false;
  const m = [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  return m.length > 0;
}

export function tieneComprobacionLabrada(row: IActuacionListItem): boolean {
  const num = row.acta_comprobacion_num?.trim();
  if (!num) return false;
  const mot = (row.comprobacion_motivo ?? "").trim();
  return Boolean(mot && mot !== "PENDIENTE");
}

export function tieneInspeccionLabrada(row: IActuacionListItem): boolean {
  return Boolean(row.acta_inspeccion_num?.trim());
}

export function tieneClausuraLabrada(row: IActuacionListItem): boolean {
  return Boolean(row.acta_clausura_num?.trim());
}

export function tieneDecomisoLabrado(row: IActuacionListItem): boolean {
  return Boolean(row.acta_decomiso_num?.trim());
}

export function kilosDecomisoPropios(row: IActuacionListItem): number {
  if (!tieneDecomisoLabrado(row)) return 0;
  const k = Number(row.decomiso_kilos_total);
  return Number.isFinite(k) && k > 0 ? k : 0;
}

/** Indicadores alineados a la lista esperada por producto / D1c. */
export function computeActuacionesPdfResumenRows(items: IActuacionListItem[]): ActuacionPdfResumenPair[] {
  let inspeccionActas = 0;
  let comprobacionActas = 0;
  let notificacionActas = 0;
  let clausuraActas = 0;
  let decomisoActas = 0;

  let inspeccionDenuncia = 0;
  let reinspeccionNotificacion = 0;
  let reinspeccionOficio = 0;
  let ratifClausura = 0;
  let ratifDecomiso = 0;
  let verificarInformar = 0;
  let kgTotal = 0;

  const total = items.length;

  for (const row of items) {
    if (tieneInspeccionLabrada(row)) inspeccionActas += 1;
    if (tieneNotificacionLabradaMotivos(row)) notificacionActas += 1;
    if (tieneComprobacionLabrada(row)) comprobacionActas += 1;
    if (tieneClausuraLabrada(row)) clausuraActas += 1;
    if (tieneDecomisoLabrado(row)) decomisoActas += 1;

    if (isInspeccionIntegralOrDenuncia(row)) inspeccionDenuncia += 1;
    if (isReinspeccionPorNotificacion(row)) reinspeccionNotificacion += 1;
    if (isReinspeccionPorOficio(row)) reinspeccionOficio += 1;

    if (isRatificacionClausura(row)) ratifClausura += 1;
    if (isRatificacionDecomiso(row)) ratifDecomiso += 1;

    const tipo = normalizeTipoExport(row.tipo_actuacion);
    if (tipo === "VERIFICAR E INFORMAR") verificarInformar += 1;

    kgTotal += kilosDecomisoPropios(row);
  }

  const fmtKg = kgTotal <= 0 ? "0" : kgTotal >= 100 ? String(Math.round(kgTotal)) : kgTotal.toFixed(1);

  return [
    { indicator: "Actuaciones realizadas", value: String(total) },
    { indicator: "Inspección Integral o Denuncia", value: String(inspeccionDenuncia) },
    { indicator: "Reinspecciones por Notificación", value: String(reinspeccionNotificacion) },
    { indicator: "Reinspecciones por Oficio", value: String(reinspeccionOficio) },
    { indicator: "Actas de inspección", value: String(inspeccionActas) },
    { indicator: "Actas de comprobación", value: String(comprobacionActas) },
    { indicator: "Actas de notificación", value: String(notificacionActas) },
    { indicator: "Actas de clausura", value: String(clausuraActas) },
    { indicator: "Actas de decomiso", value: String(decomisoActas) },
    { indicator: "Ratificaciones de clausura", value: String(ratifClausura) },
    { indicator: "Ratificaciones de decomiso", value: String(ratifDecomiso) },
    { indicator: "Verificar e informar", value: String(verificarInformar) },
    { indicator: "Mercadería decomisada (kg)", value: fmtKg },
  ];
}
