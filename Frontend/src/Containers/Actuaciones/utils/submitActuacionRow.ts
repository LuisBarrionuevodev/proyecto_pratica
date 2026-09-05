import type { ActaCanalQuitarTipo, IActuacionListItem } from "../../../api/actuacionesListApi";
import { postQuitarActaCanalActas } from "../../../api/actuacionesListApi";
import { updateActuacion } from "../../../api/actuacionesApi";
import { validateRow } from "../../../api/gridApi";
import { isReinspeccionOficioCircuitRow } from "../../../shared/reinspeccionOficio/isReinspeccionOficioCircuitRow";
import { omiteIdentidadOperativaRow } from "../../../shared/circuitoOperativo/resolveCircuitoOperativo";
import type { ReinspeccionOficioValidationContextInput } from "../../../shared/reinspeccionOficio/usaInspeccionNormalReinspeccionOficio";
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
import { buildInspectoresForCanal, inspectoresListEqual } from "./buildInspectoresForCanal";
import {
  actuacionCrudValidationContext,
  validateActuacionFormForSubmit,
} from "../validations/actuacionFormValidation";
import { normalizeActuacionRowForCrudSubmit, detectActasClearedByUser } from "../validations/actuacionFormNormalize";
import { applyContraproducenciaClearFlag } from "./contraproducenciaCrudOptions";
import { applyContribuyenteClearFlag } from "./contribuyenteCrudOptions";
import { detectBlockedActaClearAttempt } from "./actuacionEditRules";
import { isReinspeccionPorNotificacion } from "./actuacionesExportPdfResumen";
import {
  domicilioCalleCargadaEditable,
  domicilioEsTipoEsquina,
  domicilioNumeroEditable,
} from "../../../utils/domicilioCalleUi";
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
  "can_edit_domicilio",
  "domicilio_edit_blocked_reason",
  "establecimiento_operativo_id",
  "establecimiento_actuaciones_en_ficha",
  "resultado_cumplimiento_oficio",
  "notificacion_previa_num",
  "comprobacion_previa_num",
] as const;

/** Campos operativos de reinspección por oficio: dueños del POST `corregir-cierre-oficio`. */
const OFICIO_OPERATIONAL_PUT_OMIT_KEYS = [
  "contraproducencia",
  "realizo_nueva_inspeccion",
  "limpiar_contraproducencia",
] as const;

export type SanitizeActuacionPutOptions = {
  /**
   * Fuerza omitir campos operativos Oficio en PUT.
   * Por defecto se infiere desde `documentacion_contexto.circuito === REINSPECCION_OFICIO`.
   */
  omitOficioOperationalFields?: boolean;
};

export function sanitizeActuacionRowForCanalActasPut(
  row: IActuacionListItem,
  options?: SanitizeActuacionPutOptions
): IActuacionListItem {
  const copy: Record<string, unknown> = { ...row };

  for (const key of ACTUACION_CANAL_PUT_OMIT_KEYS) {
    delete copy[key];
  }

  const omitOficioOperational =
    options?.omitOficioOperationalFields ?? isReinspeccionOficioCircuitRow(row);

  if (omitOficioOperational) {
    for (const key of OFICIO_OPERATIONAL_PUT_OMIT_KEYS) {
      delete copy[key];
    }
  } else {
    const contra = String(copy.contraproducencia ?? "").trim();
    copy.contraproducencia = contra || null;
  }

  return {
    ...(copy as IActuacionListItem),
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
  };
}

/** UUID fijo válido para validar filas desde la vista de actuaciones. */
export const ACTUACION_TABLE_UI_BATCH_ID = "00000000-0000-0000-0000-000000000001";

function applyDomicilioCalleSubmitGuard(
  row: IActuacionListItem,
  originalRow?: IActuacionListItem | null
): IActuacionListItem {
  const baseline = originalRow ?? row;
  let out: IActuacionListItem = row;

  if (row.can_edit_domicilio === true) {
    const baselineCalle = domicilioCalleCargadaEditable(baseline);
    const baselineNumero = domicilioNumeroEditable(baseline);
    const editedCalle = String(row.calle ?? "").trim();
    const editedNumero = String(row.numero ?? "").trim();
    const calleChanged = editedCalle !== baselineCalle;
    const numeroChanged = editedNumero !== baselineNumero;
    if (calleChanged || numeroChanged) {
      const calle = editedCalle || baselineCalle;
      const numero = editedNumero || baselineNumero;
      return {
        ...out,
        calle: calle || null,
        numero: numero || null,
        numero_tipo: domicilioEsTipoEsquina(row) ? "ESQUINA" : row.numero_tipo ?? "NUMERO",
      };
    }
    const copy: Record<string, unknown> = { ...out };
    delete copy.calle;
    delete copy.numero;
    delete copy.numero_tipo;
    return copy as IActuacionListItem;
  }

  // PR7.15d: domicilio bloqueado — no validar ni enviar calle/número (aunque estén en el draft).
  const blockedCopy: Record<string, unknown> = { ...out };
  delete blockedCopy.calle;
  delete blockedCopy.numero;
  delete blockedCopy.numero_tipo;
  return blockedCopy as IActuacionListItem;
}

/** FIX.9 — Circuito RN/Oficio: el PUT residual no es dueño de identidad operativa. */
function applyCircuitoResidualOperationalStrip(
  row: IActuacionListItem,
  originalRow?: IActuacionListItem | null,
  oficioValidationContext?: ReinspeccionOficioValidationContextInput
): IActuacionListItem {
  const esOficio =
    isReinspeccionOficioCircuitRow(row) ||
    oficioValidationContext != null ||
    Boolean(originalRow && isReinspeccionOficioCircuitRow(originalRow));
  const omiteIdentidad =
    omiteIdentidadOperativaRow(row) ||
    (originalRow != null && omiteIdentidadOperativaRow(originalRow)) ||
    esOficio;
  if (!omiteIdentidad) return row;

  const copy: Record<string, unknown> = { ...row };
  if (row.can_edit_domicilio !== true) {
    delete copy.calle;
    delete copy.numero;
    delete copy.numero_tipo;
  }
  if (row.can_edit_rubro !== true) {
    delete copy.rubro_nombre;
  }
  delete copy.contrib_apellido;
  delete copy.contrib_nombre;
  delete copy.razon_social;
  delete copy.doc_nro;
  delete copy.nombre_local;
  return copy as IActuacionListItem;
}

/** @deprecated Usar applyCircuitoResidualOperationalStrip */
function applyOficioResidualOperationalStrip(
  row: IActuacionListItem,
  originalRow?: IActuacionListItem | null,
  oficioValidationContext?: ReinspeccionOficioValidationContextInput
): IActuacionListItem {
  return applyCircuitoResidualOperationalStrip(row, originalRow, oficioValidationContext);
}

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
  /** Tras `corregir-cierre-oficio`: omitir campos operativos del PUT genérico. */
  oficioCorrectionApplied?: boolean;
  /** Actas ya quitadas por `corregir-cierre-oficio` en el mismo Guardar (evita doble delete). */
  actasClearedByOficioCorrection?: ActaCanalQuitarTipo[];
  /** Estado destino del formulario Oficio para validación contextualizada (FIX.4.1). */
  oficioValidationContext?: ReinspeccionOficioValidationContextInput;
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
  const {
    id,
    fullRow,
    originalRow,
    oficioCorrectionApplied = false,
    actasClearedByOficioCorrection = [],
    oficioValidationContext,
    skipValidation,
    skipUpdate,
    onBeforeSave,
    onAfterSave,
    onValidationPassed,
  } = params;

  let rowToSubmit = fullRow;

  if (!skipValidation) {
    const rowForValidation =
      oficioValidationContext != null
        ? {
            ...fullRow,
            tipo_actuacion: oficioValidationContext.subtipo.trim() || fullRow.tipo_actuacion,
          }
        : fullRow;
    const clientValidation = validateActuacionFormForSubmit(
      rowForValidation,
      actuacionCrudValidationContext(rowForValidation, {
        originalRow,
        oficioValidationContext,
      })
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
  rowToSubmit = applyContribuyenteClearFlag(originalRow, rowToSubmit);
  const correccionCierre = Boolean(rowToSubmit.limpiar_contraproducencia);

  rowToSubmit = applyDomicilioCalleSubmitGuard(rowToSubmit, originalRow);
  rowToSubmit = applyOficioResidualOperationalStrip(
    rowToSubmit,
    originalRow,
    oficioValidationContext
  );

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
  const alreadyCleared = new Set(actasClearedByOficioCorrection);
  const actasPendingClear = actasToClear.filter(({ tipo }) => !alreadyCleared.has(tipo));
  const esReinspeccionNotificacion =
    (originalRow != null && isReinspeccionPorNotificacion(originalRow)) ||
    isReinspeccionPorNotificacion(rowToSubmit);
  const tieneContraproducenciaFinal =
    !correccionCierre &&
    !rowToSubmit.limpiar_contraproducencia &&
    Boolean(String(rowToSubmit.contraproducencia ?? "").trim());
  const actasQuitarEnPutTransaccional =
    actasPendingClear.length > 0 && (esReinspeccionNotificacion || tieneContraproducenciaFinal);

  const rowForCanal = sanitizeActuacionRowForCanalActasPut(rowToSubmit);
  const inspectores = buildInspectoresForCanal(rowForCanal);
  const rowWithInspectores: IActuacionListItem & { actas_a_quitar?: ActaCanalQuitarTipo[] } = {
    ...rowForCanal,
  };
  if (originalRow) {
    const baselineInspectores = buildInspectoresForCanal(originalRow);
    if (inspectores.length > 0 || !inspectoresListEqual(inspectores, baselineInspectores)) {
      rowWithInspectores.inspectores = inspectores;
    }
  } else if (inspectores.length > 0) {
    rowWithInspectores.inspectores = inspectores;
  }
  if (actasQuitarEnPutTransaccional) {
    rowWithInspectores.actas_a_quitar = actasPendingClear.map(({ tipo }) => tipo);
  }

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
      if (!actasQuitarEnPutTransaccional) {
        for (const { tipo } of actasPendingClear) {
          await postQuitarActaCanalActas(id, tipo);
        }
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
