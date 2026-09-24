import type { IActuacionListItem } from "../../../api/actuacionesListApi";

function trim(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

function filaTieneContribuyente(row: IActuacionListItem): boolean {
  return Boolean(
    trim(row.doc_nro) ||
      trim(row.contrib_apellido) ||
      trim(row.contrib_nombre) ||
      trim(row.razon_social)
  );
}

/**
 * True si la fila baseline traía algún dato de contribuyente al abrir edición.
 */
export function baselineTeniaContribuyente(
  original: IActuacionListItem | null | undefined
): boolean {
  return original != null && filaTieneContribuyente(original);
}

/**
 * True si el usuario vació explícitamente todos los campos de contribuyente respecto al baseline.
 */
export function detectContribuyenteClearedByUser(
  original: IActuacionListItem,
  draft: IActuacionListItem
): boolean {
  return baselineTeniaContribuyente(original) && !filaTieneContribuyente(draft);
}

/**
 * Marca `limpiar_contribuyente` para el PUT cuando el usuario borró titular en edición.
 * El mapper backend traduce esto a `contribuyente: null` (clear explícito, no preserve).
 */
export function applyContribuyenteClearFlag(
  original: IActuacionListItem | null | undefined,
  row: IActuacionListItem
): IActuacionListItem {
  if (!original || !detectContribuyenteClearedByUser(original, row)) {
    return row;
  }
  return {
    ...row,
    limpiar_contribuyente: true,
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    razon_social: null,
  };
}
