import type { GridRow } from "../../../api/gridApi";
import {
  createEmptyRow,
  createEmptyRows,
  extractDataColumns,
} from "../../CargarActuaciones/utils/gridHelpers";
import { COLUMN_DEFINITIONS } from "../config/columnDefinitions";
import {
  formatRelevadorCellValue,
  parseRelevadorCellValue,
  relevadorIdsToLabel,
} from "./relevamientoRelevadorCell";

export const RELEVAMIENTO_DRAFT_STORAGE_VERSION = 2;

const EDITABLE_FIELD_IDS = COLUMN_DEFINITIONS.map((c) => c.id);

export type RelevamientoDraftStoredRow = {
  clientRowId: string;
  fields: Record<string, unknown>;
  relevadorIds?: number[];
};

export type RelevamientoDraftStoragePayload = {
  version: number;
  drafts: RelevamientoDraftStoredRow[];
};

/**
 * Key aislada por usuario (username estable de sesión).
 */
export function relevamientoDraftStorageKey(username: string): string {
  return `digitaliza:relevamientos:draft:v${RELEVAMIENTO_DRAFT_STORAGE_VERSION}:${username}`;
}

export function isPersistedRelevamientoGridRow(row: GridRow): boolean {
  return row.ID !== undefined && row.ID !== null;
}

function hasMeaningfulDraftFieldValue(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

/**
 * Fila local con datos relevantes y sin ID de backend.
 */
export function isMeaningfulRelevamientoDraft(row: GridRow): boolean {
  if (isPersistedRelevamientoGridRow(row)) return false;
  const fields = pickRelevamientoDraftFields(row);
  const ids = (row as GridRow & { _relevadorIds?: number[] })._relevadorIds;
  if (Array.isArray(ids) && ids.length > 0) return true;
  return Object.values(fields).some(hasMeaningfulDraftFieldValue);
}

export function pickRelevamientoDraftFields(row: GridRow): Record<string, unknown> {
  const data = extractDataColumns(row) as Record<string, unknown>;
  const fields: Record<string, unknown> = {};
  for (const id of EDITABLE_FIELD_IDS) {
    if (id in data) fields[id] = data[id];
  }
  return fields;
}

export function serializeRelevamientoDraftRows(rows: GridRow[]): RelevamientoDraftStoredRow[] {
  return rows
    .filter(isMeaningfulRelevamientoDraft)
    .filter((row) => Boolean(row._rowId))
    .map((row) => {
      const extended = row as GridRow & { _relevadorIds?: number[] };
      return {
        clientRowId: row._rowId!,
        fields: pickRelevamientoDraftFields(row),
        relevadorIds: extended._relevadorIds?.length ? [...extended._relevadorIds] : undefined,
      };
    });
}

export function draftStoredRowToGridRow(
  draft: RelevamientoDraftStoredRow,
  catalog?: { id: number; nombre: string }[]
): GridRow {
  const fields = { ...draft.fields };
  if (draft.relevadorIds?.length && catalog?.length) {
    const label = relevadorIdsToLabel(draft.relevadorIds, catalog);
    if (label) fields.Relevador = label;
  }
  return {
    _rowId: draft.clientRowId,
    _state: "PENDIENTE",
    _cellErrors: {},
    _touched: true,
    _needsCommit: true,
    _relevadorIds: draft.relevadorIds,
    ...fields,
  } as GridRow;
}

function isValidDraftPayload(value: unknown): value is RelevamientoDraftStoragePayload {
  if (!value || typeof value !== "object") return false;
  const v = value as RelevamientoDraftStoragePayload;
  if (v.version !== RELEVAMIENTO_DRAFT_STORAGE_VERSION) return false;
  if (!Array.isArray(v.drafts)) return false;
  return v.drafts.every(
    (d) =>
      d &&
      typeof d === "object" &&
      typeof d.clientRowId === "string" &&
      d.fields &&
      typeof d.fields === "object"
  );
}

export function readRelevamientoDrafts(username: string | null | undefined): RelevamientoDraftStoredRow[] {
  if (!username) return [];
  const key = relevamientoDraftStorageKey(username);
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!isValidDraftPayload(parsed)) {
      sessionStorage.removeItem(key);
      return [];
    }
    return parsed.drafts;
  } catch {
    sessionStorage.removeItem(key);
    return [];
  }
}

export function writeRelevamientoDrafts(username: string | null | undefined, rows: GridRow[]): void {
  if (!username) return;
  const key = relevamientoDraftStorageKey(username);
  const drafts = serializeRelevamientoDraftRows(rows);
  if (drafts.length === 0) {
    sessionStorage.removeItem(key);
    return;
  }
  const payload: RelevamientoDraftStoragePayload = {
    version: RELEVAMIENTO_DRAFT_STORAGE_VERSION,
    drafts,
  };
  sessionStorage.setItem(key, JSON.stringify(payload));
}

export function syncRelevamientoDraftsAfterGridChange(
  username: string | null | undefined,
  rows: GridRow[]
): void {
  writeRelevamientoDrafts(username, rows);
}

export function buildInitialRelevamientoGridData(
  drafts: RelevamientoDraftStoredRow[],
  catalog?: { id: number; nombre: string }[]
): GridRow[] {
  if (drafts.length === 0) return createEmptyRows(5);
  const draftRows = drafts.map((d) => draftStoredRowToGridRow(d, catalog));
  const minTrailingEmpty = 5;
  const emptyCount = Math.max(minTrailingEmpty, 2);
  return [...draftRows, ...createEmptyRows(emptyCount)];
}

export function createEmptyRowPreservingId(rowId?: string): GridRow {
  if (!rowId) return createEmptyRow();
  return {
    ...createEmptyRow(),
    _rowId: rowId,
  };
}

/** Sincroniza ids internos tras editar la celda Relevador. */
export function syncRelevadorIdsOnRow(
  row: GridRow,
  catalog: { id: number; nombre: string }[]
): GridRow {
  const nombres = parseRelevadorCellValue(row.Relevador);
  const ids = nombres.length
    ? catalog
        .filter((c) => nombres.some((n) => n.toUpperCase() === c.nombre.toUpperCase()))
        .map((c) => c.id)
    : [];
  return {
    ...row,
    Relevador: formatRelevadorCellValue(nombres),
    _relevadorIds: ids,
  } as GridRow;
}
