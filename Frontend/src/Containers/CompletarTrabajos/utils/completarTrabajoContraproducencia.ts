/**
 * Contraproducencia «no permite inspección» (catálogo backend `catalog_contraproducencia.nombre`).
 * Completar trabajo: exige acta de comprobación + motivo; clausura opcional.
 */
export const CONTRAPRODUCCION_NO_PERMITE_INSPECCION = "NO PERMITE INSPECCION";

/** Motivo de comprobación canónico (catálogo) alineado a «no permite inspección». */
export const MOTIVO_COMPROBACION_NO_PERMITE_INSPECCION = "No Permite la Inspección";

export const AYUDA_NO_PERMITE_INSPECCION_CIERRE =
  "Sin acta de comprobación, el trabajo volverá a urgentes. Con comprobación, continuará su seguimiento mediante el acta.";

/** Reingreso con corrección de rubro (Completar trabajo). */
export const CORRECTIVA_NO_ES_EL_RUBRO = "NO ES EL RUBRO";

/** Reingreso con corrección de domicilio (Completar trabajo). */
export const CORRECTIVA_DIRECCION_INCORRECTA = "DIRECCION INCORRECTA";

function looseKey(s: string): string {
  return s
    .toUpperCase()
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim()
    .normalize("NFD")
    .replace(/\u0300-\u036f/g, "");
}

export function esNoPermiteInspeccionContraproducencia(value: string | null | undefined): boolean {
  const t = (value ?? "").trim();
  if (!t) return false;
  return looseKey(t) === looseKey(CONTRAPRODUCCION_NO_PERMITE_INSPECCION);
}

export function esMotivoComprobacionNoPermiteInspeccion(value: string | null | undefined): boolean {
  const t = (value ?? "").trim();
  if (!t) return false;
  return looseKey(t) === looseKey(MOTIVO_COMPROBACION_NO_PERMITE_INSPECCION);
}

export function esCorrectivaRubroContraproducencia(value: string | null | undefined): boolean {
  const t = (value ?? "").trim();
  if (!t) return false;
  return looseKey(t) === looseKey(CORRECTIVA_NO_ES_EL_RUBRO);
}

export function esCorrectivaDireccionContraproducencia(value: string | null | undefined): boolean {
  const t = (value ?? "").trim();
  if (!t) return false;
  return looseKey(t) === looseKey(CORRECTIVA_DIRECCION_INCORRECTA);
}
