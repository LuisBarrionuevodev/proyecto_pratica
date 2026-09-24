/** Valores canónicos persistidos / API (turno de carga). */
export const TURNO_CANON = {
  MANIANA: "MANIANA",
  TARDE: "TARDE",
} as const;

const CANON_TO_LABEL: Record<string, string> = {
  "": "",
  [TURNO_CANON.MANIANA]: "Mañana",
  [TURNO_CANON.TARDE]: "Tarde",
};

/** Opciones visibles para el dropdown Glide (valor mostrado = etiqueta). */
export const TURNO_DROPDOWN_LABELS = ["", "Mañana", "Tarde"] as const;

export function turnoStoredToDropdownLabel(value: string | null | undefined): string | null {
  if (value == null || value === "") return null;
  const u = String(value).trim().toUpperCase().replace("Ñ", "N");
  const canon = u === "MANIANA" || u === "MANANA" ? TURNO_CANON.MANIANA : u === "TARDE" ? TURNO_CANON.TARDE : String(value).trim();
  return CANON_TO_LABEL[canon] ?? null;
}

export function turnoDropdownLabelToStored(label: string | null | undefined): string | null {
  if (label == null || label === "") return null;
  const n = String(label).trim().toUpperCase().replace("Ñ", "N");
  if (n === "MANANA" || n === "MANIANA") return TURNO_CANON.MANIANA;
  if (n === "TARDE") return TURNO_CANON.TARDE;
  return null;
}

/** Etiqueta visible para bandejas / listados (MANIANA → Mañana). */
export function turnoCargaLabel(value: string | null | undefined): string {
  return turnoStoredToDropdownLabel(value) ?? (value?.trim() ? value.trim() : "—");
}
