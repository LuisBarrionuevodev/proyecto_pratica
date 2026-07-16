import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import { updateRelevamiento } from "../../../api/relevamientosApi";
import { validateRow } from "../../../api/gridApi";
import {
  domicilioCalleCargadaEditable,
  domicilioEsTipoEsquina,
  domicilioNumeroEditable,
} from "../../../utils/domicilioCalleUi";
import { applyEstablecimientoCamposToPayload } from "./relevamientoCamposForm";

/** Campos de solo lectura / display que no deben ir al PUT. */
const RELEVAMIENTO_PUT_OMIT_KEYS = [
  "calle_normalizada",
  "calle_estado",
  "calle_score",
  "calle_sugerida",
  "calle_mostrar",
  "calle_catalogo_id",
  "calle_raw",
  "calle_cargada",
  "calle_ingresada",
  "esquina_normalizada",
  "esquina_catalogo_id",
  "esquina_status",
  "esquina_score",
  "esquina_raw",
  "numero_esquina",
  "numero_mostrar",
  "domicilio_id",
  "iniciador_ruta_id",
  "iniciador_estado",
  "editable",
] as const;

/**
 * Asegura calle/número editables en payload sin vaciar domicilio ni reenviar metadata stale.
 */
export function applyRelevamientoDomicilioSubmitGuard(
  row: IRelevamientoListItem,
  originalRow?: IRelevamientoListItem | null
): IRelevamientoListItem {
  const baseline = originalRow ?? row;
  const baselineCalle = domicilioCalleCargadaEditable(baseline);
  const baselineNumero = domicilioNumeroEditable(baseline);
  const editedCalle = String(row.calle ?? "").trim();
  const editedNumero = String(row.numero ?? "").trim();

  const isEsquina = domicilioEsTipoEsquina(row);
  const numero_tipo = isEsquina ? "ESQUINA" : "NUMERO";
  const calle = editedCalle || baselineCalle;
  const numero = editedNumero || baselineNumero;

  const copy: Record<string, unknown> = { ...row };
  for (const key of RELEVAMIENTO_PUT_OMIT_KEYS) {
    delete copy[key];
  }

  return {
    ...(copy as IRelevamientoListItem),
    calle: calle || null,
    numero: numero || null,
    numero_tipo,
  };
}

/** Mapeo de errores (grid / backend → claves de columna de la tabla). */
export const RELEVAMIENTO_ROW_ERROR_KEY_MAP: Record<string, string> = {
  Fecha: "fecha",
  Inspector: "inspector",
  Calle: "calle",
  Numero: "numero",
  Rubro: "rubro",
  "Nombre fantasía": "nombre_fantasia",
  "Ángulo esquina": "angulo_esquina",
  Turno: "turno",
  "Está abierto": "esta_abierto",
  /** Duplicados / reglas de fila completa (backend grid validate): mostrar junto al domicilio. */
  _row: "calle",
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
export function buildRelevamientoGridRow(row: IRelevamientoListItem) {
  return {
    ID: row.id,
    Fecha: row.fecha,
    Inspector: row.inspector,
    Calle: row.calle,
    Numero: row.numero,
    Rubro: row.rubro,
    "Nombre fantasía": row.nombre_fantasia ?? "",
    "Ángulo esquina": row.angulo_esquina ?? "",
    Turno: row.turno ?? "",
    "Está abierto":
      row.esta_abierto === true ? "Sí" : row.esta_abierto === false ? "No" : "",
  };
}

/**
 * Normaliza valores de edición (selects MRT) al shape que acepta el API.
 */
export function normalizeRelevamientoRowForApi(row: IRelevamientoListItem): IRelevamientoListItem {
  const copy = applyEstablecimientoCamposToPayload({ ...row });
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
  /** Fila original al abrir el modal (para no pisar domicilio con metadata stale). */
  originalRow?: IRelevamientoListItem | null;
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
    originalRow,
  } = params;

  const fullRow = applyRelevamientoDomicilioSubmitGuard(
    normalizeRelevamientoRowForApi(rawFullRow),
    originalRow
  );

  if (!skipValidation && batchId) {
    const v = await validateRow({
      batch_id: batchId,
      row_id: `rel_${id}`,
      row: buildRelevamientoGridRow(fullRow) as any,
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
