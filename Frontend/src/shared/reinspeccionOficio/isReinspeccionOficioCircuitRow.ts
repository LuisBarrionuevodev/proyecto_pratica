import type { IActuacionListItem } from "../../api/actuacionesListApi";

/**
 * True si la fila pertenece al circuito operativo REINSPECCION_OFICIO.
 * Los campos operativos de este circuito solo los persiste POST corregir-cierre-oficio.
 */
export function isReinspeccionOficioCircuitRow(
  row: Pick<IActuacionListItem, "documentacion_contexto">
): boolean {
  return row.documentacion_contexto?.circuito === "REINSPECCION_OFICIO";
}
