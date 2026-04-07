import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { updateActuacion } from "../../../api/actuacionesApi";
import { validateRow } from "../../../api/gridApi";

/**
 * El canal **Cargar actuación** (PUT grilla) no admite expediente/oficio administrativos en el cuerpo;
 * el presenter los incluye en GET para lectura. Se deben anular antes de validar y enviar.
 */
export function sanitizeActuacionRowForCanalActasPut(row: IActuacionListItem): IActuacionListItem {
  return {
    ...row,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
  };
}

/** UUID fijo válido para validar filas desde la vista de actuaciones. */
export const ACTUACION_TABLE_UI_BATCH_ID = "00000000-0000-0000-0000-000000000001";

/** Mapeo de errores (backend → snake_case de la tabla). */
export const ACTUACION_ROW_ERROR_KEY_MAP: Record<string, string> = {
  "Orden de trabajo": "orden_trabajo_numero",
  "Fecha actuación": "fecha_actuacion",
  "Tipo actuación": "tipo_actuacion",
  Contraproducencia: "contraproducencia",
  "Inspector 1": "inspector1",
  "Inspector 2": "inspector2",
  "Inspector 3": "inspector3",
  Calle: "calle",
  Número: "numero",
  Rubro: "rubro_nombre",
  Apellido: "contrib_apellido",
  Nombre: "contrib_nombre",
  DNI: "doc_nro",
  "Acta inspección": "acta_inspeccion_num",
  "Acta notificación": "acta_notificacion_num",
  "Motivo notif 1": "notificacion_motivo_1",
  "Motivo notif 2": "notificacion_motivo_2",
  "Motivo notif 3": "notificacion_motivo_3",
  "Acta comprobación": "acta_comprobacion_num",
  "Motivo comprobación": "comprobacion_motivo",
  "Acta clausura": "acta_clausura_num",
  "Acta decomiso": "acta_decomiso_num",
  "Kilos decomiso": "decomiso_kilos_total",
  "Nombre local": "nombre_local",
  "Acta notificación previa": "notificacion_previa_num",
  "Acta comprobación previa": "comprobacion_previa_num",
  "Expediente año": "expediente_anio",
  "Expediente número": "expediente_numero",
  "Oficio año": "oficio_anio",
  "Oficio número": "oficio_numero",
  "Oficio causa": "oficio_causa",
};

export function normalizeActuacionRowErrors(errors?: Record<string, string>): Record<string, string> {
  if (!errors) return {};
  const mapped: Record<string, string> = {};
  Object.entries(errors).forEach(([key, msg]) => {
    const targetKey = ACTUACION_ROW_ERROR_KEY_MAP[key] || key;
    mapped[targetKey] = msg;
  });
  return mapped;
}

export type SubmitActuacionRowResult =
  | { ok: true }
  | { ok: false; kind: "validation"; fieldErrors: Record<string, string> }
  | { ok: false; kind: "backend_fields"; fieldErrors: Record<string, string> }
  | { ok: false; kind: "generic"; message: string };

export type SubmitActuacionRowParams = {
  id: number;
  fullRow: IActuacionListItem;
  skipValidation: boolean;
  skipUpdate: boolean;
  onBeforeSave?: (fullRow: IActuacionListItem) => Promise<void>;
  onAfterSave?: (fullRow: IActuacionListItem) => Promise<void>;
  /**
   * Se llama solo si `skipValidation` es false y la validación de grilla pasó,
   * antes de `onBeforeSave` / PUT (misma orden que el flujo original en la tabla).
   */
  onValidationPassed?: () => void;
};

/**
 * Pipeline de guardado de una fila de actuación: validación grid → hooks → PUT.
 * Sin UI: el llamador aplica `setRowErrors` / `alert` según el resultado.
 */
export async function submitActuacionRow(params: SubmitActuacionRowParams): Promise<SubmitActuacionRowResult> {
  const { id, fullRow, skipValidation, skipUpdate, onBeforeSave, onAfterSave, onValidationPassed } = params;

  const rowForCanal = sanitizeActuacionRowForCanalActasPut(fullRow);

  if (!skipValidation) {
    const v = await validateRow({
      batch_id: ACTUACION_TABLE_UI_BATCH_ID,
      row_id: `act_${id}`,
      row: rowForCanal as any,
    });

    if (!v.ok) {
      return { ok: false, kind: "validation", fieldErrors: normalizeActuacionRowErrors(v.errors || {}) };
    }

    onValidationPassed?.();
  }

  try {
    if (onBeforeSave) {
      await onBeforeSave(rowForCanal);
    }

    if (!skipUpdate) {
      await updateActuacion(id, rowForCanal as any);
    }

    if (onAfterSave) {
      await onAfterSave(rowForCanal);
    }

    return { ok: true };
  } catch (error: unknown) {
    console.error("Error al actualizar actuación:", error);
    const err = error as { response?: { data?: { errors?: unknown; detail?: unknown } } };
    const backendErrors = err?.response?.data?.errors;
    if (backendErrors && typeof backendErrors === "object") {
      return {
        ok: false,
        kind: "backend_fields",
        fieldErrors: normalizeActuacionRowErrors(backendErrors as Record<string, string>),
      };
    }
    const msg = err?.response?.data?.detail ?? "No se pudo actualizar el registro.";
    return { ok: false, kind: "generic", message: String(msg) };
  }
}
