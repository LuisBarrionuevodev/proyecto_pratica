/** Máximo de motivos de notificación persistidos (slots backend). */
export const MOTIVOS_NOTIFICACION_MAX = 3;

/**
 * Orden estable y sin duplicados (máx. 3) a partir de valores sueltos o slots guardados.
 */
export function orderedMotivosNotificacion(selected: Iterable<string | null | undefined>): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of selected) {
    const t = (raw ?? "").trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
    if (out.length >= MOTIVOS_NOTIFICACION_MAX) break;
  }
  return out;
}

export function motivosNotificacionFromSlots(
  m1?: string | null,
  m2?: string | null,
  m3?: string | null
): string[] {
  return orderedMotivosNotificacion([m1, m2, m3]);
}

export function slotsToMotivosApi(selected: Iterable<string | null | undefined>): {
  m1: string;
  m2: string;
  m3: string;
} {
  const o = orderedMotivosNotificacion(selected);
  return {
    m1: o[0] ?? "",
    m2: o[1] ?? "",
    m3: o[2] ?? "",
  };
}

/** Unión catálogo + valores ya elegidos (p. ej. históricos fuera de catálogo). */
export function mergeMotivosNotifCatalogStrings(catalog: string[], actuales: string[]): string[] {
  const set = new Set<string>(catalog.map((x) => x.trim()).filter(Boolean));
  for (const a of actuales) {
    const t = (a ?? "").trim();
    if (t) set.add(t);
  }
  return [...set].sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
}
