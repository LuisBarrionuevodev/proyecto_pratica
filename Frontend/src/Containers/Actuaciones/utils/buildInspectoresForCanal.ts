import type { IActuacionListItem } from "../../../api/actuacionesListApi";

function fromInspectorSlots(row: IActuacionListItem): string[] {
  return [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
}

/**
 * Lista de inspectores para validación grid y PUT canal actas.
 * Prioriza `inspectores` del backend si tiene elementos; si es `[]` vacío, usa inspector1/2/3.
 */
export function buildInspectoresForCanal(row: IActuacionListItem): string[] {
  if (Array.isArray(row.inspectores) && row.inspectores.length > 0) {
    return row.inspectores.map((s) => String(s).trim()).filter(Boolean);
  }
  return fromInspectorSlots(row);
}

/**
 * Compara listas de inspectores (orden importa).
 */
export function inspectoresListEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((name, idx) => name === b[idx]);
}
