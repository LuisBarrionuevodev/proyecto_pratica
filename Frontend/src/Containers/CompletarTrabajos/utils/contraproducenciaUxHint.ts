import {
  CONTRAPRODUCCION_NO_PERMITE_INSPECCION,
  CORRECTIVA_DIRECCION_INCORRECTA,
  CORRECTIVA_NO_ES_EL_RUBRO,
} from "./completarTrabajoContraproducencia";

/**
 * Mensajes UX según contraproducencia elegida (alineado al backend: no existe local vs reingreso).
 */
export type ContraproducenciaUxHint =
  | "cierra_sin_reingreso"
  | "reingreso_prioridad_alta"
  | "correctiva_rubro_direccion"
  | "no_permite_inspeccion";

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

/** Valores de catálogo / alias que el backend trata como cierre sin reingreso. */
const NO_REINGRESO_KEYS = new Set([
  looseKey("NO EXISTE"),
  looseKey("NO EXISTE NO COINCIDE RUBRO"),
  looseKey("NO EXISTE NO ES EL RUBRO"),
  looseKey("NO_EXISTE_LOCAL"),
  looseKey("NO EXISTE LOCAL"),
  looseKey("NO EXISTE/NO ES EL RUBRO"),
]);

/**
 * Misma familia que `STORED_REINGRESO_ALTA` / `normalize_contraproducencia` en backend:
 * LOCAL CERRADO, CLIMA, ZONA ROJA, NO_HUBO, OTROS → reingreso con prioridad alta.
 */
const REINGRESO_KEYS = new Set([
  looseKey("LOCAL CERRADO"),
  looseKey("LOCAL_CERRADO"),
  looseKey("CLIMA"),
  looseKey("ZONA ROJA"),
  looseKey("ZONA_ROJA"),
  looseKey("NO HUBO"),
  looseKey("NO_HUBO"),
  looseKey("OTROS"),
]);

export function getContraproducenciaUxHint(selected: string): ContraproducenciaUxHint | null {
  const t = selected.trim();
  if (!t) return null;
  const k = looseKey(t);
  if (NO_REINGRESO_KEYS.has(k)) return "cierra_sin_reingreso";
  if (k === looseKey(CONTRAPRODUCCION_NO_PERMITE_INSPECCION)) return "no_permite_inspeccion";
  if (k === looseKey(CORRECTIVA_NO_ES_EL_RUBRO) || k === looseKey(CORRECTIVA_DIRECCION_INCORRECTA)) {
    return "correctiva_rubro_direccion";
  }
  if (REINGRESO_KEYS.has(k)) return "reingreso_prioridad_alta";
  return null;
}
