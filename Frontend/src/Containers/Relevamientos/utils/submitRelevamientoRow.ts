import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import { updateRelevamiento } from "../../../api/relevamientosApi";
import { validateRow } from "../../../api/gridApi";

/** Mapeo de errores (grid / backend → claves de columna de la tabla). */
export const RELEVAMIENTO_ROW_ERROR_KEY_MAP: Record<string, string> = {
  Fecha: "fecha",
  Inspector: "inspector",
  Calle: "calle",
  Numero: "numero",
  Rubro: "rubro",
  Turno: "turno",
  "Está abierto": "esta_abierto",
};

export function normalizeRelevamientoRowErrors(errors?: Record<string, string>): Record<string, string> {
  if (!errors) return {};
  const mapped: Record<string, string> = {};
  Object.entries(errors).forEach(([key, msg]) => {
    const targetKey = RELEVAMIENTO_ROW_ERROR_KEY_MAP[key] || key;
    mapped[targetKey] = msg;
  });
  return mapped;
}

/**
 * Fila en el shape que espera el validador de grilla para el batch de relevamientos.
 */
function buildGridRow(row: IRelevamientoListItem) {
  return {
    ID: row.id,
    Fecha: row.fecha,
    Inspector: row.inspector,
    Calle: row.calle,
    Numero: row.numero,
    Rubro: row.rubro,
    Turno: row.turno ?? "",
    "Está abierto":
      row.esta_abierto === true ? "Sí" : row.esta_abierto === false ? "No" : "",
  };
}

/**
 * Normaliza valores de edición (selects MRT) al shape que acepta el API.
 */
export function normalizeRelevamientoRowForApi(row: IRelevamientoListItem): IRelevamientoListItem {
  const copy = { ...row };
  const ea = copy.esta_abierto as unknown;
  if (ea === "Sí" || ea === "Si" || ea === "si") copy.esta_abierto = true;
  else if (ea === "No" || ea === "no") copy.esta_abierto = false;
  else if (ea === "" || ea === undefined) copy.esta_abierto = null;
  if (copy.turno === "") copy.turno = null;
  return copy;
}

export type SubmitRelevamientoRowResult =
  | { ok: true }
  | { ok: false; kind: "validation"; fieldErrors: Record<string, string> }
  | { ok: false; kind: "backend_fields"; fieldErrors: Record<string, string> }
  | { ok: false; kind: "generic"; message: string };

export type SubmitRelevamientoRowParams = {
  id: number;
  /** Fila ya mergeada (original + valores de edición); se normaliza antes del API. */
  fullRow: IRelevamientoListItem;
  /**
   * Batch de grilla devuelto por `startBatch("relevamientos")`.
   * Si es `null` (fallo al iniciar batch), no se valida aunque `skipValidation` sea false (mismo criterio que antes en la tabla).
   */
  batchId: string | null;
  skipValidation: boolean;
  skipUpdate: boolean;
  onBeforeSave?: (fullRow: IRelevamientoListItem) => Promise<void>;
  onAfterSave?: (fullRow: IRelevamientoListItem) => Promise<void>;
  /**
   * Tras validar (o saltarla si no hay batch / skipValidation), antes de hooks y PUT.
   * Equivale a limpiar errores de la fila antes del intento de persistencia, como hacía la tabla.
   */
  onBeforePersist?: () => void;
};

/**
 * Pipeline de guardado de una fila de relevamiento: validación grid (si hay batch) → hooks → PUT.
 * Sin UI: el llamador aplica `setRowErrors` / `alert` / `exitEditingMode` según el resultado.
 */
export async function submitRelevamientoRow(
  params: SubmitRelevamientoRowParams
): Promise<SubmitRelevamientoRowResult> {
  const {
    id,
    fullRow: rawFullRow,
    batchId,
    skipValidation,
    skipUpdate,
    onBeforeSave,
    onAfterSave,
    onBeforePersist,
  } = params;

  const fullRow = normalizeRelevamientoRowForApi(rawFullRow);

  if (!skipValidation && batchId) {
    const v = await validateRow({
      batch_id: batchId,
      row_id: `rel_${id}`,
      row: buildGridRow(fullRow) as any,
    });

    if (!v.ok) {
      return {
        ok: false,
        kind: "validation",
        fieldErrors: normalizeRelevamientoRowErrors(v.errors || {}),
      };
    }
  }

  onBeforePersist?.();

  try {
    if (onBeforeSave) {
      await onBeforeSave(fullRow);
    }

    if (!skipUpdate) {
      await updateRelevamiento(id, fullRow as any);
    }

    if (onAfterSave) {
      await onAfterSave(fullRow);
    }

    return { ok: true };
  } catch (error: unknown) {
    console.error("Error al actualizar relevamiento:", error);
    const err = error as { response?: { data?: { errors?: unknown; detail?: unknown } } };
    const backendErrors = err?.response?.data?.errors;
    if (backendErrors && typeof backendErrors === "object") {
      return {
        ok: false,
        kind: "backend_fields",
        fieldErrors: normalizeRelevamientoRowErrors(backendErrors as Record<string, string>),
      };
    }
    const msg = err?.response?.data?.detail ?? "No se pudo actualizar el registro.";
    return { ok: false, kind: "generic", message: String(msg) };
  }
}
