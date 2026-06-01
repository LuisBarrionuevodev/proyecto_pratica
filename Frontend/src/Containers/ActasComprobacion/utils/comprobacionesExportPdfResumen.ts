/**
 * Indicadores del bloque ACTAS DE COMPROBACIÓN (PDF export).
 */
import type { ComprobacionExportRow, ComprobacionExportSlice } from "./comprobacionExportTypes";
import {
  esCumplida,
  motivoExport,
  normalizeMotivoKey,
  tieneExpedienteEnvio,
  tieneExpedienteRespuesta,
  tieneOficio,
} from "./comprobacionesExportShared";

export type ComprobacionPdfResumenPair = {
  indicator: string;
  value: string;
};

const SIN_RUBRO = "Sin rubro";

function countBySlice(items: ComprobacionExportRow[], slice: ComprobacionExportSlice): number {
  return items.filter((r) => r.exportSlice === slice).length;
}

function countMotivos(items: ComprobacionExportRow[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of items) {
    const m = motivoExport(row);
    if (!m) continue;
    const key = normalizeMotivoKey(m);
    if (!key) continue;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
}

function countByRubro(items: ComprobacionExportRow[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of items) {
    const rubro = normalizeMotivoKey(row.rubro) || SIN_RUBRO;
    counts.set(rubro, (counts.get(rubro) ?? 0) + 1);
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

/** Comprobaciones con resultado CUMPLE o NO_CUMPLE (reinspección/visita cerrada). */
export function countConResultadoCumplimiento(items: ComprobacionExportRow[]): number {
  return items.filter((r) => {
    const rc = r.resultadoCumplimiento.toUpperCase();
    return rc === "CUMPLE" || rc === "NO_CUMPLE";
  }).length;
}

export function computeComprobacionesPdfResumenRows(items: ComprobacionExportRow[]): ComprobacionPdfResumenPair[] {
  const motivos = countMotivos(items);
  const rubros = countByRubro(items);
  const topMotivo = topEntry(motivos);
  const topRubro = topEntry(rubros);

  const fmtTop = (entry: { label: string; count: number } | null) =>
    entry ? `${entry.label} (${entry.count})` : "—";

  return [
    { indicator: "Actas de comprobación en el período", value: String(items.length) },
    {
      indicator: "Actas con expediente de envío",
      value: String(items.filter((r) => tieneExpedienteEnvio(r)).length),
    },
    { indicator: "Actas con oficio", value: String(items.filter((r) => tieneOficio(r)).length) },
    {
      indicator: "Actas con expediente de respuesta",
      value: String(items.filter((r) => tieneExpedienteRespuesta(r)).length),
    },
    { indicator: "Actas cumplidas (CUMPLE)", value: String(items.filter((r) => esCumplida(r)).length) },
    { indicator: "Pendientes de expediente", value: String(countBySlice(items, "expediente")) },
    { indicator: "Pendientes de oficio", value: String(countBySlice(items, "oficio")) },
    { indicator: "Pendientes de reinspección", value: String(countBySlice(items, "reinspeccion")) },
    { indicator: "Top motivo más frecuente", value: fmtTop(topMotivo) },
    { indicator: "Top 5 motivos más frecuentes", value: topNFormatted(motivos, 5) },
    {
      indicator: "Top rubro con más actas de comprobación",
      value: topRubro ? `${topRubro.label} (${topRubro.count})` : "—",
    },
    {
      indicator: "Top 5 rubros con más actas de comprobación",
      value: topNFormatted(rubros, 5),
    },
  ];
}
