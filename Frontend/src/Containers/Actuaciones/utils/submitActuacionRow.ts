import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { updateActuacion } from "../../../api/actuacionesApi";
import { validateRow } from "../../../api/gridApi";
import {
  DEFAULT_FIELD_ERROR_SUMMARY,
  mapApiErrorsToFormState,
  type FormErrorsFromApi,
} from "../../../utils/parseApiError";
import { buildInspectoresForCanal } from "./buildInspectoresForCanal";

/**
 * El canal **Cargar actuación** (PUT grilla) no admite expediente/oficio administrativos en el cuerpo;
 * el presenter los incluye en GET para lectura. Se deben anular antes de validar y enviar.
 */
export function sanitizeActuacionRowForCanalActasPut(row: IActuacionListItem): IActuacionListItem {
  const {
    ec5_uuid: _omitEc5,
    has_epicollect_detalle: _omitDet,
    epicollect_non_media_field_count: _omitCnt,
    epicollect_preview: _omitPrev,
    epicollect_sectores_condiciones: _omitSec,
    epicollect_otros_preview: _omitOtros,
    epicollect_evidencias_total: _omitEviTot,
    epicollect_evidencias_grupos: _omitEviGrp,
    ...rowSinEc5
  } = row;
  const contra = (rowSinEc5.contraproducencia ?? "").trim();
  return {
    ...rowSinEc5,
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
  oficio_anio: "oficio_anio",
  oficio_causa: "oficio_causa",
  oficio: "oficio_numero",
  expediente_numero: "expediente_numero",
  expediente_anio: "expediente_anio",
  expediente: "expediente_numero",
};

export const ACTUACION_FORM_ERROR_OPTIONS = {
  fieldKeyAliases: ACTUACION_ROW_ERROR_KEY_MAP,
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
  return {
    fieldErrors: normalizeActuacionRowErrors(parsed.fieldErrors),
    globalMessage: parsed.globalMessage,
  };
}

export type SubmitActuacionRowResult =
  | { ok: true }
  | { ok: false; kind: "validation"; fieldErrors: Record<string, string>; globalMessage?: string | null }
  | { ok: false; kind: "backend_fields"; fieldErrors: Record<string, string>; globalMessage?: string | null }
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
  const inspectores = buildInspectoresForCanal(rowForCanal);
  const rowWithInspectores = { ...rowForCanal, inspectores };

  if (!skipValidation) {
    const v = await validateRow({
      batch_id: ACTUACION_TABLE_UI_BATCH_ID,
      row_id: `act_${id}`,
      row: rowWithInspectores as any,
    });

    if (!v.ok) {
      const fe = normalizeActuacionRowErrors(v.errors || {});
      const hasFe = Object.keys(fe).length > 0;
      return {
        ok: false,
        kind: "validation",
        fieldErrors: fe,
        globalMessage: hasFe ? DEFAULT_FIELD_ERROR_SUMMARY : (v.errors?._row ?? null),
      };
    }

    onValidationPassed?.();
  }

  try {
    if (onBeforeSave) {
      await onBeforeSave(rowWithInspectores);
    }

    if (!skipUpdate) {
      await updateActuacion(id, rowWithInspectores as any);
    }

    if (onAfterSave) {
      await onAfterSave(rowWithInspectores);
    }

    return { ok: true };
  } catch (error: unknown) {
    console.error("Error al actualizar actuación:", error);
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
