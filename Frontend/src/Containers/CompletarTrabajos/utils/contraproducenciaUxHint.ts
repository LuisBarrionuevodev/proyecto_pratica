import { CONTRAPRODUCCION_NO_PERMITE_INSPECCION } from "./completarTrabajoContraproducencia";

/**
 * Mensajes UX según contraproducencia elegida (alineado al backend: no existe local vs reingreso).
 */
export type ContraproducenciaUxHint =
  | "cierra_sin_reingreso"
  | "reingreso_prioridad_alta"
  | "no_permite_inspeccion";

function looseKey(s: string): string {
  return s
    .toUpperCase()
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim();
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

/** Cerrado: LOCAL_CERRADO, CLIMA, ZONA_ROJA, NO_HUBO → reingreso con prioridad alta. */
const REINGRESO_KEYS = new Set([
  looseKey("LOCAL CERRADO"),
  looseKey("LOCAL_CERRADO"),
  looseKey("CLIMA"),
  looseKey("ZONA ROJA"),
  looseKey("ZONA_ROJA"),
  looseKey("NO HUBO"),
  looseKey("NO_HUBO"),
]);

export function getContraproducenciaUxHint(selected: string): ContraproducenciaUxHint | null {
  const t = selected.trim();
  if (!t) return null;
  const k = looseKey(t);
  if (NO_REINGRESO_KEYS.has(k)) return "cierra_sin_reingreso";
  if (k === looseKey(CONTRAPRODUCCION_NO_PERMITE_INSPECCION)) return "no_permite_inspeccion";
  if (REINGRESO_KEYS.has(k)) return "reingreso_prioridad_alta";
  return null;
}
