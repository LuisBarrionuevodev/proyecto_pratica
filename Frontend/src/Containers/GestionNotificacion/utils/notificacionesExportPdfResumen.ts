/**
 * Indicadores del bloque NOTIFICACIONES BROMATOLÓGICAS (PDF export Gestión Notificación).
 */
import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { DIAS_EN_PLAZO_MIN, POR_VENCER_MAX, POR_VENCER_MIN } from "../gestionNotificacionPlazo";
import {
  motivosNotificacionList,
  normalizeMotivoKey,
  plazoInicialDias,
  tieneComprobacionPosterior,
} from "./notificacionesExportShared";

export type NotificacionPdfResumenPair = {
  indicator: string;
  value: string;
};

const SIN_RUBRO = "Sin rubro";

function countMotivos(items: IActuacionesPendientesItem[], slot: 0 | 1 | 2): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of items) {
    const list = motivosNotificacionList(row);
    const raw = list[slot];
    if (!raw) continue;
    const key = normalizeMotivoKey(raw);
    if (!key) continue;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
}

function countAllMotivos(items: IActuacionesPendientesItem[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of items) {
    for (const m of motivosNotificacionList(row)) {
      const key = normalizeMotivoKey(m);
      if (!key) continue;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return counts;
}

function topEntry(counts: Map<string, number>): { label: string; count: number } | null {
  let best: { label: string; count: number } | null = null;
  for (const [label, count] of counts) {
    if (!best || count > best.count) best = { label, count };
  }
  return best;
}

function topNFormatted(counts: Map<string, number>, n: number): string {
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
  if (!sorted.length) return "—";
  return sorted.map(([label, count]) => `${label} (${count})`).join(", ");
}

function countByRubro(items: IActuacionesPendientesItem[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of items) {
    const rubro = normalizeMotivoKey(row.rubro_nombre) || SIN_RUBRO;
    counts.set(rubro, (counts.get(rubro) ?? 0) + 1);
  }
  return counts;
}

/**
 * Plazos otorgados = notificaciones con plazo inicial documentado (días en notificación).
 */
export function countNotificacionesConPlazoInicial(items: IActuacionesPendientesItem[]): number {
  return items.filter((r) => plazoInicialDias(r) != null).length;
}

export function sumProrrogasOtorgadas(items: IActuacionesPendientesItem[]): number {
  return items.reduce((acc, r) => {
    const p = r.plazos_otorgados;
    if (p == null || !Number.isFinite(Number(p))) return acc;
    return acc + Math.max(0, Number(p));
  }, 0);
}

export function countVencidasOHoy(items: IActuacionesPendientesItem[]): number {
  return items.filter((r) => r.dias_restantes === 0).length;
}

export function countPorVencer(items: IActuacionesPendientesItem[]): number {
  return items.filter((r) => {
    const d = r.dias_restantes;
    return d != null && d >= POR_VENCER_MIN && d <= POR_VENCER_MAX;
  }).length;
}

export function countEnPlazo(items: IActuacionesPendientesItem[]): number {
  return items.filter((r) => r.dias_restantes != null && r.dias_restantes >= DIAS_EN_PLAZO_MIN).length;
}

export function countReinspeccionesConComprobacionPosterior(items: IActuacionesPendientesItem[]): number {
  return items.filter((r) => tieneComprobacionPosterior(r)).length;
}

export function computeNotificacionesPdfResumenRows(
  items: IActuacionesPendientesItem[]
): NotificacionPdfResumenPair[] {
  const total = items.length;
  const rubros = countByRubro(items);
  const topRubro = topEntry(rubros);
  const allMotivos = countAllMotivos(items);
  const topMotivo = topEntry(allMotivos);
  const m1 = topEntry(countMotivos(items, 0));
  const m2 = topEntry(countMotivos(items, 1));
  const m3 = topEntry(countMotivos(items, 2));

  const fmtTop = (entry: { label: string; count: number } | null) =>
    entry ? `${entry.label} (${entry.count})` : "—";

  return [
    { indicator: "Notificaciones en el período", value: String(total) },
    {
      indicator: "Notificaciones con plazo inicial",
      value: String(countNotificacionesConPlazoInicial(items)),
    },
    { indicator: "Prórrogas otorgadas (total)", value: String(sumProrrogasOtorgadas(items)) },
    { indicator: "En plazo", value: String(countEnPlazo(items)) },
    { indicator: "Por vencer", value: String(countPorVencer(items)) },
    { indicator: "Vencidas o hoy", value: String(countVencidasOHoy(items)) },
    {
      indicator: "Top rubro con más notificaciones",
      value: topRubro ? `${topRubro.label} (${topRubro.count})` : "—",
    },
    {
      indicator: "Top 5 rubros con más notificaciones",
      value: topNFormatted(rubros, 5),
    },
    {
      indicator: "Motivo / infracción más recurrente",
      value: fmtTop(topMotivo),
    },
    { indicator: "Motivo 1 más recurrente", value: fmtTop(m1) },
    { indicator: "Motivo 2 más recurrente", value: fmtTop(m2) },
    { indicator: "Motivo 3 más recurrente", value: fmtTop(m3) },
    {
      indicator: "Reinspecciones con acta de comprobación posterior",
      value: String(countReinspeccionesConComprobacionPosterior(items)),
    },
  ];
}
