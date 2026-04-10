/**
 * Contraproducencia «no permite inspección» (catálogo backend `catalog_contraproducencia.nombre`).
 * Completar trabajo: exige acta de comprobación + motivo; clausura opcional.
 */
export const CONTRAPRODUCCION_NO_PERMITE_INSPECCION = "NO PERMITE INSPECCION";

function looseKey(s: string): string {
  return s
    .toUpperCase()
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim();
}

export function esNoPermiteInspeccionContraproducencia(value: string | null | undefined): boolean {
  const t = (value ?? "").trim();
  if (!t) return false;
  return looseKey(t) === looseKey(CONTRAPRODUCCION_NO_PERMITE_INSPECCION);
}
