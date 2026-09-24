import { validateRow, commitBatch, type GridRow } from "../../../api/gridApi";
import type { AppFeedback } from "../../../components/feedback/GlobalFeedbackProvider";
import { applyFormErrorsFromMap } from "../../../utils/parseApiError";
import {
  ACTUACION_FIELD_ERROR_SUMMARY,
  normalizeActuacionApiError,
} from "../../Actuaciones/validations/normalizeActuacionApiError";
import { notifyActuacionApiError } from "../../Actuaciones/utils/actuacionSaveFeedback";
import { runCargarActuacionPostSaveCleanup } from "./cargarActuacionModalLifecycle";

const INTERNAL_ERR_TO_GLIDE: Record<string, string> = {
  orden_trabajo_numero: "Orden de trabajo",
  fecha_actuacion: "Fecha actuación",
  rubro_nombre: "Rubro",
  contrib_apellido: "Apellido",
  contrib_nombre: "Nombre",
  razon_social: "Razón social",
  doc_nro: "DNI",
  acta_inspeccion_num: "Acta inspección",
  items_acta_inspeccion: "Condiciones de inspección",
  cantidad_personas_sin_carnet_sanidad: "Personas sin carnet de sanidad",
  acta_notificacion_num: "Acta notificación",
  notificacion_motivo_1: "Motivo notif 1",
  notificacion_motivo_2: "Motivo notif 2",
  notificacion_motivo_3: "Motivo notif 3",
  acta_comprobacion_num: "Acta comprobación",
  comprobacion_motivo: "Motivo comprobación",
  acta_clausura_num: "Acta clausura",
  acta_decomiso_num: "Acta decomiso",
  decomiso_kilos_total: "Kilos decomiso",
  inspectores: "Inspectores",
  calle: "Calle",
  numero: "Número",
  carga_solo_comprobacion: "Cargar solo comprobación",
};

export const CARGAR_ACTUACION_ERROR_OPTIONS = {
  fieldKeyAliases: INTERNAL_ERR_TO_GLIDE,
  fallbackMessage: "Error al validar o guardar.",
} as const;

function toCargarGlideFieldErrors(errors: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(errors)) {
    out[INTERNAL_ERR_TO_GLIDE[k] ?? k] = v;
  }
  return out;
}

export type SubmitCargarActuacionNuevaDeps = {
  batchId: string;
  rowId: string;
  payload: Partial<GridRow>;
  feedback: AppFeedback;
  resetForm: () => void;
  closeModal: () => void;
  setFieldErrors: (errors: Record<string, string>) => void;
};

/**
 * Valida y confirma una fila de Cargar Actuación (validate-row → commit-batch).
 * Errores de red/API van al catch; éxito con cleanup UI aislado del catch.
 */
export async function submitCargarActuacionNuevaRow(deps: SubmitCargarActuacionNuevaDeps): Promise<void> {
  const { batchId, rowId, payload, feedback, resetForm, closeModal, setFieldErrors } = deps;

  try {
    const response = await validateRow({
      batch_id: batchId,
      row_id: rowId,
      row: payload as GridRow,
    });

    const validation = applyFormErrorsFromMap(response.errors, CARGAR_ACTUACION_ERROR_OPTIONS);
    setFieldErrors(validation.fieldErrors);

    if (!response.ok || !response.normalized) {
      if (validation.globalMessage) {
        feedback.warning(validation.globalMessage);
      } else if (Object.keys(validation.fieldErrors).length > 0) {
        feedback.warning(ACTUACION_FIELD_ERROR_SUMMARY);
      }
      return;
    }

    const commitResp = await commitBatch({
      batch_id: batchId,
      rows: [{ row_id: rowId, normalized: response.normalized as unknown as GridRow }],
    });

    const mine = commitResp.results?.find((r) => r.row_id === rowId);
    if (mine?.ok) {
      runCargarActuacionPostSaveCleanup({
        success: (message) => feedback.success(message),
        resetForm,
        closeModal,
      });
      return;
    }

    const commit = applyFormErrorsFromMap(mine?.errors, CARGAR_ACTUACION_ERROR_OPTIONS);
    setFieldErrors(commit.fieldErrors);
    const commitMsg = commit.globalMessage ?? "No se pudo confirmar la carga.";
    feedback.warning(commitMsg);
  } catch (e: unknown) {
    const normalized = normalizeActuacionApiError(e, CARGAR_ACTUACION_ERROR_OPTIONS);
    setFieldErrors(toCargarGlideFieldErrors(normalized.fieldErrors));
    notifyActuacionApiError(normalized, feedback);
  }
}
