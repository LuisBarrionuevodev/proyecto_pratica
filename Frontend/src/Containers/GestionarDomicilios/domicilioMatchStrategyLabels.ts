/** Labels humanos para estrategia de match del nomenclador (PR6A.1). */

const MATCH_STRATEGY_LABELS: Record<string, string> = {
  exact_nombre: "Coincidencia exacta",
  exact_key: "Coincidencia normalizada",
  exact_tokens: "Tokens exactos",
  alias: "Alias validado",
  token_containment: "Contención de tokens",
  fuzzy: "Coincidencia aproximada",
};

const STRONG_MATCH_STRATEGIES = new Set([
  "exact_nombre",
  "exact_key",
  "exact_tokens",
  "alias",
  "token_containment",
]);

function isAmbiguousReason(confidenceReason: string | null | undefined): boolean {
  return (confidenceReason ?? "").toLowerCase().includes("ambigua");
}

/** Label humano; nunca expone el enum crudo. */
export function labelMatchStrategy(
  strategy: string | null | undefined,
  confidenceReason?: string | null
): string {
  if (isAmbiguousReason(confidenceReason)) return "Ambiguo";
  const key = (strategy ?? "").trim();
  if (!key) return "—";
  return MATCH_STRATEGY_LABELS[key] ?? "—";
}

/**
 * Banda visual del score unificado según estrategia (no altera el número).
 * Estrategias fuertes → OK; ambigüedad → Revisar; fuzzy bajo → Pendiente/Revisar según score.
 */
export function labelScoreBandWithStrategy(
  score: number | null | undefined,
  matchStrategy?: string | null,
  confidenceReason?: string | null
): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  if (isAmbiguousReason(confidenceReason)) return "Revisar";
  const strategy = (matchStrategy ?? "").trim();
  if (strategy && STRONG_MATCH_STRATEGIES.has(strategy)) return "OK";
  if (strategy === "fuzzy") {
    const n = Math.round(Number(score));
    if (n >= 90) return "OK";
    if (n >= 60) return "Revisar";
    return "Pendiente";
  }
  const n = Math.round(Number(score));
  if (n >= 90) return "OK";
  if (n >= 60) return "Revisar";
  return "Pendiente";
}

export function scoreDisplayWithStrategy(
  score: number | null | undefined,
  matchStrategy?: string | null,
  confidenceReason?: string | null
): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  const num = String(Math.round(Number(score)));
  const band = labelScoreBandWithStrategy(score, matchStrategy, confidenceReason);
  return band === "—" ? num : `${num} · ${band}`;
}
