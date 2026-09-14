import { COLUMN_DEFINITIONS } from "../config/columnDefinitions";

/**
 * Offset histórico canvas/mangled — NO usar para `gridSelection`, `appendRow` ni `onKeyDown`
 * (Glide usa índices de columna de datos 0..n-1 en esas APIs).
 */
export const RELEVAMIENTO_ROW_MARKERS_BOTH_OFFSET = 1;

/** Índice de columna de datos del primer campo editable (Relevador). */
export const RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX = 0;

/** Índice de columna de datos del último campo editable ("Está abierto"). */
export const RELEVAMIENTO_LAST_EDITABLE_COL_INDEX = COLUMN_DEFINITIONS.length - 1;

/** Penúltima editable (Turno) — Glide a veces salta Está abierto sin handler explícito. */
export const RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX = RELEVAMIENTO_LAST_EDITABLE_COL_INDEX - 1;

/** IDs en orden canónico de navegación TAB (misma definición que la grilla). */
export const RELEVAMIENTO_EDITABLE_COLUMN_IDS = COLUMN_DEFINITIONS.map((c) => c.id);

export function isRelevamientoLastEditableCol(dataCol: number): boolean {
  return dataCol === RELEVAMIENTO_LAST_EDITABLE_COL_INDEX;
}

export function isRelevamientoFirstEditableCol(dataCol: number): boolean {
  return dataCol === RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX;
}

export function isRelevamientoEditableDataCol(dataCol: number): boolean {
  return dataCol >= RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX && dataCol <= RELEVAMIENTO_LAST_EDITABLE_COL_INDEX;
}

/** Normaliza coordenada de columna a índice de datos (0..7). */
export function relevamientoNormalizeDataCol(col: number): number | null {
  if (isRelevamientoEditableDataCol(col)) return col;
  const legacyMangled = col - RELEVAMIENTO_ROW_MARKERS_BOTH_OFFSET;
  if (isRelevamientoEditableDataCol(legacyMangled)) return legacyMangled;
  return null;
}

/**
 * Celda activa al presionar TAB.
 * Prioriza `gridSelection` (celda actual); `event.location` puede anticipar el destino.
 */
export function relevamientoResolveTabDataCol(
  eventLocation: readonly [number, number] | undefined,
  selectionCell: readonly [number, number] | undefined
): { dataCol: number; row: number } | null {
  if (selectionCell) {
    const dataCol = relevamientoNormalizeDataCol(selectionCell[0]);
    if (dataCol !== null) return { dataCol, row: selectionCell[1] };
  }
  if (eventLocation) {
    const dataCol = relevamientoNormalizeDataCol(eventLocation[0]);
    if (dataCol !== null) return { dataCol, row: eventLocation[1] };
  }
  return null;
}

export type RelevamientoTabForwardStep =
  | { type: "next-col"; dataCol: number; row: number }
  | { type: "next-row-first-col"; row: number }
  | { type: "append-row-first-col" };

/**
 * TAB custom en dos casos puntuales (resto: Glide nativo):
 * - Turno → Está abierto (misma fila)
 * - Está abierto → Relevador fila siguiente / append
 */
export function resolveRelevamientoTabForwardStep(
  dataCol: number,
  row: number,
  numRows: number
): RelevamientoTabForwardStep | null {
  if (dataCol === RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX) {
    return { type: "next-col", dataCol: RELEVAMIENTO_LAST_EDITABLE_COL_INDEX, row };
  }
  if (!isRelevamientoLastEditableCol(dataCol)) return null;
  if (row >= numRows - 1) return { type: "append-row-first-col" };
  return { type: "next-row-first-col", row: row + 1 };
}

export type RelevamientoShiftTabBackwardStep =
  | { type: "prev-col"; dataCol: number; row: number }
  | { type: "prev-row-last-col"; row: number };

/**
 * SHIFT+TAB custom:
 * - Está abierto → Turno
 * - Relevador → Está abierto fila anterior
 */
export function resolveRelevamientoShiftTabBackwardStep(
  dataCol: number,
  row: number
): RelevamientoShiftTabBackwardStep | null {
  if (dataCol === RELEVAMIENTO_LAST_EDITABLE_COL_INDEX) {
    return { type: "prev-col", dataCol: RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX, row };
  }
  if (!isRelevamientoFirstEditableCol(dataCol)) return null;
  if (row <= 0) return null;
  return { type: "prev-row-last-col", row: row - 1 };
}

/** Celda `[dataCol, row]` para `gridSelection` / `appendRow`. */
export function relevamientoDataColGridCell(dataCol: number, row: number): [number, number] {
  return [dataCol, row];
}

export function relevamientoRelevadorGridCell(row: number): [number, number] {
  return relevamientoDataColGridCell(RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX, row);
}

/** @deprecated usar relevamientoRelevadorGridCell */
export const relevamientoInspectorGridCell = relevamientoRelevadorGridCell;

export function relevamientoLastEditableGridCell(row: number): [number, number] {
  return relevamientoDataColGridCell(RELEVAMIENTO_LAST_EDITABLE_COL_INDEX, row);
}

export function relevamientoRelevadorDataCol(): number {
  return RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX;
}

/** @deprecated usar relevamientoRelevadorDataCol */
export const relevamientoInspectorDataCol = relevamientoRelevadorDataCol;
