import type { IActuacionListItem } from "../../../api/actuacionesListApi";

export const OBSERVACIONES_VISITA_MAX_LENGTH = 4000;

/** Texto para modo lectura del modal CRUD (`—` si vacío). */
export function observacionesVisitaDisplayText(row: IActuacionListItem): string {
  const s = (row.observaciones_ejecucion ?? "").trim();
  return s || "—";
}

/** Solo actuaciones con ítem de ruta y edición permitida pueden persistir observaciones. */
export function canEditObservacionesVisita(row: IActuacionListItem): boolean {
  if (row.actuacion_editable === false) {
    return false;
  }
  const id = row.ruta_item_id;
  return id != null && id > 0;
}

export function buildObservacionesEjecucionPutFields(
  row: IActuacionListItem
): Pick<IActuacionListItem, "observaciones_ejecucion"> {
  if (!canEditObservacionesVisita(row)) {
    return {};
  }
  const trimmed = (row.observaciones_ejecucion ?? "").trim();
  return { observaciones_ejecucion: trimmed || null };
}

export function validateObservacionesVisitaFields(
  row: IActuacionListItem
): Record<string, string> {
  if (!canEditObservacionesVisita(row)) {
    return {};
  }
  const len = (row.observaciones_ejecucion ?? "").length;
  if (len > OBSERVACIONES_VISITA_MAX_LENGTH) {
    return {
      observaciones_ejecucion: `Máximo ${OBSERVACIONES_VISITA_MAX_LENGTH} caracteres.`,
    };
  }
  return {};
}
