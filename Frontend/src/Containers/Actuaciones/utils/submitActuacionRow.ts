import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { postQuitarActaCanalActas } from "../../../api/actuacionesListApi";
import { updateActuacion } from "../../../api/actuacionesApi";import { validateRow } from "../../../api/gridApi";
import {
  DEFAULT_FIELD_ERROR_SUMMARY,
  mapApiErrorsToFormState,
  type FormErrorsFromApi,
} from "../../../utils/parseApiError";
import {
  ACTUACION_ROW_ONLY_ERROR_KEYS,
  buildActuacionFormGlobalError,
  finalizeActuacionFormErrors,
} from "./actuacionFormErrors";
import { buildInspectoresForCanal } from "./buildInspectoresForCanal";
import {
  actuacionCrudValidationContext,
  validateActuacionFormForSubmit,
} from "../validations/actuacionFormValidation";
import { normalizeActuacionRowForCrudSubmit, detectActasClearedByUser } from "../validations/actuacionFormNormalize";
import { applyContraproducenciaClearFlag } from "./contraproducenciaCrudOptions";
import { detectBlockedActaClearAttempt } from "./actuacionEditRules";
/**
 * El canal **Cargar actuación** (PUT grilla) no admite expediente/oficio administrativos en el cuerpo;
 * el presenter los incluye en GET para lectura. Se deben omitir antes de validar y enviar.
 */
const ACTUACION_CANAL_PUT_OMIT_KEYS = [
  "ec5_uuid",
  "has_epicollect_detalle",
  "epicollect_non_media_field_count",
  "epicollect_preview",
  "epicollect_sectores_condiciones",
  "epicollect_otros_preview",
  "epicollect_evidencias_total",
  "epicollect_evidencias_grupos",
  "documentacion_contexto",
  "origen_reinspeccion_oficio",
  "origen_reinspeccion_notificacion",
  "inspectores_texto",
  "numero_mostrar",
  "esquina_raw",
  "esquina_normalizada",
  "esquina_catalogo_id",
  "esquina_status",
  "esquina_score",
  "calle_normalizada",
  "calle_estado",
  "calle_score",
  "calle_sugerida",
  "calle_mostrar",
  "calle_catalogo_id",
  "calle_ingresada",
  "numero_esquina",
  "notificacion_editable",
  "comprobacion_editable",
  "establecimiento_operativo_id",
  "establecimiento_actuaciones_en_ficha",
  "resultado_cumplimiento_oficio",
  "notificacion_previa_num",
  "comprobacion_previa_num",
] as const;

export function sanitizeActuacionRowForCanalActasPut(row: IActuacionListItem): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };

  for (const key of ACTUACION_CANAL_PUT_OMIT_KEYS) {
    delete copy[key];
  }

  const contra = String(copy.contraproducencia ?? "").trim();

  return {
    ...(copy as IActuacionListItem),
    contraproducencia: contra || null,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
  };
}

/** UUID fijo válido para validar filas desde la vista de actuaciones. */
export const ACTUACION_TABLE_UI_BATCH_ID = "00000000-0000-0000-0000-000000000001";

/** Mapeo de errores (backend / grilla Glide → snake_case del modal de edición). */
export const ACTUACION_ROW_ERROR_KEY_MAP: Record<string, string> = {
  "Orden de trabajo": "orden_trabajo_numero",
  orden_trabajo_numero: "orden_trabajo_numero",
  orden_trabajo: "orden_trabajo_numero",
  "Fecha actuación": "fecha_actuacion",
  fecha_actuacion: "fecha_actuacion",
  fecha: "fecha_actuacion",
  "Tipo actuación": "tipo_actuacion",
  tipo_actuacion: "tipo_actuacion",
  tipo: "tipo_actuacion",
  Contraproducencia: "contraproducencia",
  contraproducencia: "contraproducencia",
  "Inspector 1": "inspector1",
  "Inspector 2": "inspector2",
  "Inspector 3": "inspector3",
  Inspectores: "inspectores",
  inspectores: "inspectores",
  inspector: "inspectores",
  Calle: "calle",
  calle: "calle",
  domicilio: "calle",
  Número: "numero",
  numero: "numero",
  "Tipo de numeración": "numero_tipo",
  numero_tipo: "numero_tipo",
  Rubro: "rubro_nombre",
  rubro_nombre: "rubro_nombre",
  rubro: "rubro_nombre",
  Apellido: "contrib_apellido",
  Nombre: "contrib_nombre",
  "Razón social": "razon_social",
  DNI: "doc_nro",
  "Acta inspección": "acta_inspeccion_num",
  acta_inspeccion_num: "acta_inspeccion_num",
  nro_acta_inspeccion: "acta_inspeccion_num",
  "Acta notificación": "acta_notificacion_num",
  acta_notificacion_num: "acta_notificacion_num",
  nro_acta_notificacion: "acta_notificacion_num",
  "Motivo notif 1": "notificacion_motivo_1",
  "Motivo notif 2": "notificacion_motivo_2",
  "Motivo notif 3": "notificacion_motivo_3",
  "Acta comprobación": "acta_comprobacion_num",
  acta_comprobacion_num: "acta_comprobacion_num",
  nro_acta_comprobacion: "acta_comprobacion_num",
  "Motivo comprobación": "comprobacion_motivo",
  comprobacion_motivo: "comprobacion_motivo",
  motivo: "comprobacion_motivo",
  "Acta clausura": "acta_clausura_num",
  acta_clausura_num: "acta_clausura_num",
  nro_acta_clausura: "acta_clausura_num",
  "Acta decomiso": "acta_decomiso_num",
  acta_decomiso_num: "acta_decomiso_num",
  nro_acta_decomiso: "acta_decomiso_num",
  "Kilos decomiso": "decomiso_kilos_total",
  "Nombre local": "nombre_local",
  "Acta notificación previa": "notificacion_previa_num",
  "Acta comprobación previa": "comprobacion_previa_num",
  "Expediente año": "expediente_anio",
  "Expediente número": "expediente_numero",
  "Oficio año": "oficio_anio",
  "Oficio número": "oficio_numero",
  "Oficio causa": "oficio_causa",
  oficio_numero: "oficio_numero",
  numero_oficio: "oficio_numero",
  oficio_anio: "oficio_anio",
  oficio_causa: "oficio_causa",
  oficio: "oficio_numero",
  expediente_numero: "expediente_numero",
  expediente_anio: "expediente_anio",
  expediente: "expediente_numero",
};

export const ACTUACION_FORM_ERROR_OPTIONS = {
  fieldKeyAliases: ACTUACION_ROW_ERROR_KEY_MAP,
  rowOnlyKeys: ACTUACION_ROW_ONLY_ERROR_KEYS,
  fieldErrorSummary: DEFAULT_FIELD_ERROR_SUMMARY,
  fallbackMessage: "No se pudo actualizar el registro.",
} as const;

function mapActuacionErrorKey(key: string): string {
  if (key in ACTUACION_ROW_ERROR_KEY_MAP) return ACTUACION_ROW_ERROR_KEY_MAP[key];
  if (key.startsWith("actas.")) return "acta_inspeccion_num";
  return key;
}

export function normalizeActuacionRowErrors(errors?: Record<string, string>): Record<string, string> {
  if (!errors) return {};
  const mapped: Record<string, string> = {};
  Object.entries(errors).forEach(([key, msg]) => {
    const targetKey = mapActuacionErrorKey(key);
    mapped[targetKey] = msg;
  });
  return mapped;
}

export function applyActuacionErrorsFromApi(err: unknown): FormErrorsFromApi {
  const parsed = mapApiErrorsToFormState(err, ACTUACION_FORM_ERROR_OPTIONS);
  const normalized = normalizeActuacionRowErrors(parsed.fieldErrors);
  const { fieldErrors, rowMessages } = finalizeActuacionFormErrors(normalized, {
    ignoreCrudObsoleteFields: true,
  });
  const extraRow =
    parsed.globalMessage &&
    parsed.globalMessage !== DEFAULT_FIELD_ERROR_SUMMARY &&
    !rowMessages.includes(parsed.globalMessage)
      ? [parsed.globalMessage]
      : [];
  return {
    fieldErrors,
    globalMessage: buildActuacionFormGlobalError(fieldErrors, [...rowMessages, ...extraRow]),
  };
}

export type SubmitActuacionRowResult =
  | { ok: true; correccionCierre?: boolean }
  | { ok: false; kind: "validation"; fieldErrors: Record<string, string>; globalMessage?: string | null }
  | { ok: false; kind: "backend_fields"; fieldErrors: Record<string, string>; globalMessage?: string | null }
  | { ok: false; kind: "reingreso_blocked"; message: string }
  | { ok: false; kind: "generic"; message: string };

export type SubmitActuacionRowParams = {
  id: number;
  fullRow: IActuacionListItem;
  /** Fila al abrir edición; necesaria para detectar actas vaciadas y llamar quitar-acta. */
  originalRow?: IActuacionListItem | null;
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
  const { id, fullRow, originalRow, skipValidation, skipUpdate, onBeforeSave, onAfterSave, onValidationPassed } =
    params;

  let rowToSubmit = fullRow;

  if (!skipValidation) {
    const clientValidation = validateActuacionFormForSubmit(
      fullRow,
      actuacionCrudValidationContext(fullRow, { originalRow })
    );
    if (!clientValidation.canSubmit) {
      return {
        ok: false,
        kind: "validation",
        fieldErrors: clientValidation.fieldErrors,
        globalMessage: clientValidation.globalError,
      };
    }
    rowToSubmit = normalizeActuacionRowForCrudSubmit(fullRow);
  }

  rowToSubmit = applyContraproducenciaClearFlag(originalRow, rowToSubmit);
  const correccionCierre = Boolean(rowToSubmit.limpiar_contraproducencia);

  if (originalRow) {
    const blockedMsg = detectBlockedActaClearAttempt(rowToSubmit, originalRow);
    if (blockedMsg) {
      return {
        ok: false,
        kind: "validation",
        fieldErrors: {},
        globalMessage: blockedMsg,
      };
    }
  }

  const actasToClear = originalRow ? detectActasClearedByUser(originalRow, rowToSubmit) : [];

  const rowForCanal = sanitizeActuacionRowForCanalActasPut(rowToSubmit);
  const inspectores = buildInspectoresForCanal(rowForCanal);
  const rowWithInspectores = { ...rowForCanal, inspectores };

  if (!skipValidation) {
    const v = await validateRow({
      batch_id: ACTUACION_TABLE_UI_BATCH_ID,
      row_id: `act_${id}`,
      row: rowWithInspectores as any,
    });

    if (!v.ok) {
      const rawFe = normalizeActuacionRowErrors(v.errors || {});
      const { fieldErrors, rowMessages } = finalizeActuacionFormErrors(rawFe, {
        ignoreCrudObsoleteFields: true,
      });
      if (Object.keys(fieldErrors).length > 0 || rowMessages.length > 0) {
        return {
          ok: false,
          kind: "validation",
          fieldErrors,
          globalMessage: buildActuacionFormGlobalError(fieldErrors, rowMessages),
        };
      }
    }
    onValidationPassed?.();
  }

  try {
    if (onBeforeSave) {
      await onBeforeSave(rowWithInspectores);
    }

    if (!skipUpdate) {
      for (const { tipo } of actasToClear) {
        await postQuitarActaCanalActas(id, tipo);
      }
      await updateActuacion(id, rowWithInspectores as any);
    }

    if (onAfterSave) {
      await onAfterSave(rowWithInspectores);
    }

    return { ok: true, correccionCierre };
  } catch (error: unknown) {
    console.error("Error al actualizar actuación:", error);
    const axiosLike = error as { response?: { status?: number; data?: { detail?: string } } };
    const status = axiosLike.response?.status;
    const detail = axiosLike.response?.data?.detail;
    if (status === 409 && detail) {
      return { ok: false, kind: "reingreso_blocked", message: String(detail) };
    }
    const parsed = applyActuacionErrorsFromApi(error);
    if (Object.keys(parsed.fieldErrors).length > 0) {
      return {
        ok: false,
        kind: "backend_fields",
        fieldErrors: parsed.fieldErrors,
        globalMessage: parsed.globalMessage,
      };
    }
    const msg = parsed.globalMessage ?? "No se pudo actualizar el registro.";
    return { ok: false, kind: "generic", message: msg };
  }
}
