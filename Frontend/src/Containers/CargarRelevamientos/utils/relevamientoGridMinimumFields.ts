import type { GridRow } from "../../../api/gridApi";

/** Campos mínimos solo para color “lista para enviar” en UI — sin llamadas al backend. */
export const RELEVAMIENTO_MIN_VISUAL_FIELD_IDS = [
  "Relevador",
  "Calle",
  "Numero",
  "Rubro",
] as const;

/**
 * True si la fila tiene los datos mínimos cargados (fecha no es requisito visual).
 */
export function relevamientoRowMinimumCompleteForVisual(row: GridRow): boolean {
  const strOk = (v: unknown) => {
    if (v === null || v === undefined) return false;
    return String(v).trim().length > 0;
  };
  return RELEVAMIENTO_MIN_VISUAL_FIELD_IDS.every((id) =>
    strOk(row[id as keyof GridRow])
  );
}
