/** Labels humanos para estados de clasificación compuesta (solo UI). */

const NOMENCLATURA_LABELS: Record<string, string> = {
  NOMENCLATURA_OK: "Nomenclatura OK",
  NOMENCLATURA_REVISAR: "Revisar calle",
  NOMENCLATURA_PENDIENTE: "Calle pendiente",
  VALIDADO_MANUAL: "Manual",
};

const GEOCODE_LABELS: Record<string, string> = {
  GEOCODE_OK: "Geocode OK",
  GEOCODE_REVISAR: "Revisar punto",
  GEOCODE_PENDIENTE: "Sin geocode",
  GEOCODE_ERROR: "Error geocode",
  VALIDADO_MANUAL: "Manual",
};

export function labelNomenclaturaEstado(value: string | null | undefined): string {
  const v = (value ?? "").trim();
  if (!v) return "—";
  return NOMENCLATURA_LABELS[v] ?? v.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

export function labelGeocodeEstado(value: string | null | undefined): string {
  const v = (value ?? "").trim();
  if (!v) return "—";
  return GEOCODE_LABELS[v] ?? v.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

export function labelScoreUnificado(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  const n = Math.round(Number(score));
  if (n >= 90) return "OK";
  if (n >= 60) return "Revisar";
  return "Pendiente";
}

export function scoreUnificadoNumeric(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  return String(Math.round(Number(score)));
}
