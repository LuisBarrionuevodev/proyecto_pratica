/** Prioridad visual por score unificado (PR6B — no altera cálculo). */

export type DomicilioPriorityBand = "alta" | "media" | "baja";

export function priorityBandFromScore(
  score: number | null | undefined
): DomicilioPriorityBand | null {
  if (score == null || Number.isNaN(Number(score))) return null;
  const n = Math.round(Number(score));
  if (n < 50) return "alta";
  if (n < 80) return "media";
  return "baja";
}

export function labelPriorityBand(band: DomicilioPriorityBand | null): string {
  if (!band) return "—";
  if (band === "alta") return "Alta";
  if (band === "media") return "Media";
  return "Baja";
}

export function prioritySortKey(score: number | null | undefined): number {
  if (score == null || Number.isNaN(Number(score))) return 9999;
  return Number(score);
}
