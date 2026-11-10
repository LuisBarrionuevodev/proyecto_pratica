/** Separador compacto de motivos de comprobación (lectura y texto derivado). */
export const SEPARADOR_MOTIVOS_COMPROBACION = " · ";

export type MotivosComprobacionSource = {
  motivos_comprobacion?: string[] | null;
  motivos_comprobacion_texto?: string | null;
  comprobacion_motivo?: string | null;
};

/**
 * Orden de carga, sin duplicados. No hay máximo fijo.
 */
export function orderedMotivosComprobacion(selected: Iterable<string | null | undefined>): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of selected) {
    const t = (raw ?? "").trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  return out;
}

function splitTextoMotivos(texto: string): string[] {
  if (!texto.includes(SEPARADOR_MOTIVOS_COMPROBACION)) return [texto];
  return orderedMotivosComprobacion(texto.split(SEPARADOR_MOTIVOS_COMPROBACION));
}

/**
 * Hidrata la lista de edición/lectura: arreglo canónico, si no el escalar legado
 * (salvo `PENDIENTE`). Conserva el orden de carga.
 */
export function hydrateMotivosComprobacion(row: MotivosComprobacionSource): string[] {
  const fromArr = orderedMotivosComprobacion(row.motivos_comprobacion ?? []);
  if (fromArr.length) return fromArr;
  const texto = (row.motivos_comprobacion_texto ?? "").trim();
  if (texto) return splitTextoMotivos(texto);
  const scalar = (row.comprobacion_motivo ?? "").trim();
  if (!scalar || scalar.toUpperCase() === "PENDIENTE") return [];
  return splitTextoMotivos(scalar);
}

export function motivosComprobacionTexto(motivos: Iterable<string | null | undefined>): string {
  return orderedMotivosComprobacion(motivos).join(SEPARADOR_MOTIVOS_COMPROBACION);
}

/** Lectura documental: una viñeta por motivo. */
export function motivosComprobacionLecturaMultilinea(
  motivos: Iterable<string | null | undefined>
): string {
  return orderedMotivosComprobacion(motivos)
    .map((m) => `• ${m}`)
    .join("\n");
}

export function mergeMotivosCompCatalogStrings(catalog: string[], actuales: string[]): string[] {
  const set = new Set<string>(catalog.map((x) => x.trim()).filter(Boolean));
  for (const a of actuales) {
    const t = (a ?? "").trim();
    if (t) set.add(t);
  }
  return [...set].sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
}

/** Primer ítem para el campo legado `comprobacion_motivo` (nunca el join derivado). */
export function primerMotivoComprobacionLegado(motivos: Iterable<string | null | undefined>): string | null {
  return orderedMotivosComprobacion(motivos)[0] ?? null;
}
