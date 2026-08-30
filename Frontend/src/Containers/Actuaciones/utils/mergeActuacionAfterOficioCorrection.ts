import type { IActuacionListItem } from "../../../api/actuacionesListApi";

/**
 * Campos operativos de reinspección por oficio: solo los persiste
 * `POST /actuaciones/{id}/corregir-cierre-oficio`.
 */
const OFICIO_OPERATIONAL_FROM_POST: (keyof IActuacionListItem)[] = [
  "tipo_actuacion",
  "contraproducencia",
  "resultado_cumplimiento_oficio",
  "realizo_nueva_inspeccion",
];

export type MergeActuacionAfterOficioCorrectionInput = {
  /** Respuesta canónica del POST de corrección. */
  correctedRow: IActuacionListItem;
  /** Borrador local con actas/inspectores u otros cambios CRUD pendientes. */
  pendingDraft: IActuacionListItem;
};

/**
 * Combina fila corregida por Oficio con cambios locales del modal sin reintroducir
 * contraproducencia/resultado stale del draft.
 *
 * Ownership: POST gana en campos operativos; el draft gana en el resto.
 */
export function mergeActuacionAfterOficioCorrection(
  input: MergeActuacionAfterOficioCorrectionInput
): IActuacionListItem {
  const { correctedRow, pendingDraft } = input;
  const merged: IActuacionListItem = { ...pendingDraft };

  for (const key of OFICIO_OPERATIONAL_FROM_POST) {
    if (key in correctedRow) {
      (merged as Record<string, unknown>)[key] = correctedRow[key] ?? null;
    }
  }

  if (correctedRow.documentacion_contexto) {
    merged.documentacion_contexto = correctedRow.documentacion_contexto;
  }

  return merged;
}
