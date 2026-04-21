import type { IActuacionListItem } from "../../../api/actuacionesListApi";

/**
 * Lista de inspectores para validación grid y PUT canal actas.
 * Prioriza `inspectores` del backend si existe; si no, deriva de inspector1/2/3.
 */
export function buildInspectoresForCanal(row: IActuacionListItem): string[] {
  if (Array.isArray(row.inspectores)) {
    return row.inspectores.map((s) => String(s).trim()).filter(Boolean);
  }
  return [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
}
