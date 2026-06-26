import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  esCorrectivaDireccionContraproducencia,
  esCorrectivaRubroContraproducencia,
  esNoPermiteInspeccionContraproducencia,
} from "../../CompletarTrabajos/utils/completarTrabajoContraproducencia";
import { getActuacionEditableFields } from "../utils/actuacionEditRules";
import { motivosNotificacionFromSlots } from "../../../utils/motivosNotificacionSlots";
import { buildActuacionFormGlobalError } from "../utils/actuacionFormErrors";
import { buildInspectoresForCanal } from "../utils/buildInspectoresForCanal";
import { isReinspeccionPorNotificacion } from "../utils/actuacionesExportPdfResumen";
import {
  ACTUACION_ACTA_NUM_FIELDS,
  ACTUACION_ACTA_NUM_INVALID_MSG,
  ACTUACION_DOC_NRO_INVALID_MSG,
  hasTitularPersonaOrazonSocial,
  validateAndNormalizeActaNum,
  validateDocNro,
} from "./actuacionFormNormalize";

/** Mensajes alineados a `CompletarTrabajoModal` (pre-submit) y reglas CRUD Editar Actuación. */
export const ACTUACION_VALIDATION_MESSAGES = {
  contraproducenciaVisitaNoRealizada: "Elegí una contraproducencia para visita no realizada.",
  comprobacionMotivoSiHayActa: "Si cargás acta de comprobación, elegí un motivo de comprobación.",
  comprobacionNoPermiteInspeccion:
    'Para "No permite inspección" debe cargar acta de comprobación y motivo.',
  actaInspeccionOComprobacionRequerida: "Debe cargar acta de inspección o acta de comprobación.",
  rubroCorrectiva: "Debe indicar el rubro correcto.",
  calleCorrectiva: "Con «dirección incorrecta» completá la calle corregida.",
  numeroCorrectiva: "Con «dirección incorrecta» completá el número corregido.",
  notificacionMotivo: "La notificación requiere al menos un motivo.",
  notificacionRequiereInspeccion: "Para cargar una notificación debe existir acta de inspección.",
  titularRequerido: "Debe ingresar nombre y apellido o razón social.",
  fechaRequerida: "Fecha requerida",
  fechaFormato: "Formato de fecha incorrecto (YYYY-MM-DD).",
  tipoRequerido: "Elegí el tipo de actuación.",
  calleRequerida: "Calle requerida",
  rubroRequerido: "Rubro requerido",
  inspectoresMinimoDos: "Debe seleccionar al menos dos inspectores.",
  kilosNumericos: "Kilos debe ser numérico",
  numeroNormalizadorWarning:
    "El número de domicilio se corrige desde la normalización de domicilios, no desde Actuaciones.",
} as const;

export type ActuacionFormValidationInput = Pick<
  IActuacionListItem,
  | "contraproducencia"
  | "calle"
  | "numero"
  | "rubro_nombre"
  | "fecha_actuacion"
  | "tipo_actuacion"
  | "doc_nro"
  | "contrib_apellido"
  | "contrib_nombre"
  | "razon_social"
  | "nombre_local"
  | "acta_comprobacion_num"
  | "comprobacion_motivo"
  | "acta_notificacion_num"
  | "notificacion_motivo_1"
  | "notificacion_motivo_2"
  | "notificacion_motivo_3"
  | "acta_inspeccion_num"
  | "acta_clausura_num"
  | "acta_decomiso_num"
  | "decomiso_kilos_total"
  | "inspector1"
  | "inspector2"
  | "inspector3"
  | "inspectores"
  | "notificacion_editable"
  | "comprobacion_editable"
  | "documentacion_contexto"
  | "origen_reinspeccion_notificacion"
>;

export type ActuacionFormValidationContext = {
  /** Origen del formulario (solo informativo / tests). */
  source?: "completarTrabajo" | "crud";
  /**
   * Visita realizada = sin contraproducencia (misma semántica que Completar trabajo).
   * Por defecto se infiere de `contraproducencia` vacía.
   */
  visitaRealizada?: boolean;
  /** CRUD Actuaciones: no validar ni bloquear número manual (normalizador de domicilios). */
  omitNumeroManual?: boolean;
  /** Omite reglas de acta/motivos de notificación (reinspección por notificación). */
  skipNotificacionActaRules?: boolean;
  /** Si false, no valida campos de notificación bloqueados por expediente. */
  notificacionEditable?: boolean;
  /** Si false, no valida campos de comprobación bloqueados por expediente. */
  comprobacionEditable?: boolean;
  /**
   * CRUD Actuaciones: fecha, tipo, rubro, calle, titular, documento, inspectores (≥2), actas.
   * Completar trabajo: false (solo reglas de actas/contraproducencia ya existentes).
   */
  includeCrudEditRules?: boolean;
  /**
   * Titular, documento (≥7 dígitos), inspectores (≥2 si visita realizada), formato actas,
   * notificación→inspección. Activo en CRUD y Completar trabajo.
   */
  includeSharedFormRules?: boolean;
  /**
   * Completar trabajo: acta inspección o comprobación mínima si visita realizada sin contraproducencia.
   */
  includeCompletarTrabajoRules?: boolean;
  /** CRUD: false en reinspección/ratificación/verificar e informar (no validar titular/documento). */
  canEditContribuyente?: boolean;
  /** CRUD: false en ratificación/verificar e informar (no exigir calle/rubro). */
  canEditDomicilio?: boolean;
};

export type ActuacionFormValidationResult = {
  fieldErrors: Record<string, string>;
  globalError: string | null;
  warnings: string[];
  canSubmit: boolean;
};

function trim(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

function isValidDateIso(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(value);
  return !Number.isNaN(d.getTime()) && value === d.toISOString().split("T")[0];
}

function resolveVisitaRealizada(form: ActuacionFormValidationInput, context: ActuacionFormValidationContext): boolean {
  if (context.visitaRealizada != null) return context.visitaRealizada;
  return !trim(form.contraproducencia);
}

function resolveSkipNotificacionRules(
  form: ActuacionFormValidationInput,
  context: ActuacionFormValidationContext
): boolean {
  if (context.skipNotificacionActaRules != null) return context.skipNotificacionActaRules;
  return isReinspeccionPorNotificacion(form as IActuacionListItem);
}

function validateCrudActaNumeros(fieldErrors: Record<string, string>, form: ActuacionFormValidationInput): void {
  for (const key of ACTUACION_ACTA_NUM_FIELDS) {
    const parsed = validateAndNormalizeActaNum(form[key]);
    if (!parsed.ok) {
      fieldErrors[key] = parsed.message;
    }
  }
}

/**
 * Validaciones cliente compartidas (Completar trabajo + CRUD Actuaciones).
 *
 * @param form Valores del formulario (fila o estado local del modal).
 * @param context Ajustes por pantalla (CRUD vs completar trabajo).
 * @returns Errores por campo, resumen global, advertencias no bloqueantes y `canSubmit`.
 */
export function validateActuacionFormForSubmit(
  form: ActuacionFormValidationInput,
  context: ActuacionFormValidationContext = {}
): ActuacionFormValidationResult {
  const fieldErrors: Record<string, string> = {};
  const warnings: string[] = [];

  const contra = trim(form.contraproducencia);
  const visitaRealizada = resolveVisitaRealizada(form, context);
  const esNoPermiteInspeccion = esNoPermiteInspeccionContraproducencia(contra);
  const lockedNotif = context.notificacionEditable === false || form.notificacion_editable === false;
  const lockedComp = context.comprobacionEditable === false || form.comprobacion_editable === false;
  const skipNotifRules = resolveSkipNotificacionRules(form, context);
  const omitNumero = context.omitNumeroManual === true;
  const crudEdit = context.includeCrudEditRules === true;
  const sharedRules = context.includeSharedFormRules === true || crudEdit;
  const completarRules = context.includeCompletarTrabajoRules === true;
  const tieneContraproducencia = Boolean(contra);

  if (crudEdit) {
    const fecha = trim(form.fecha_actuacion);
    if (!fecha) {
      fieldErrors.fecha_actuacion = ACTUACION_VALIDATION_MESSAGES.fechaRequerida;
    } else if (!isValidDateIso(fecha)) {
      fieldErrors.fecha_actuacion = ACTUACION_VALIDATION_MESSAGES.fechaFormato;
    }

    if (!trim(form.tipo_actuacion)) {
      fieldErrors.tipo_actuacion = ACTUACION_VALIDATION_MESSAGES.tipoRequerido;
    }

    if (context.canEditDomicilio !== false) {
      if (!trim(form.calle)) {
        fieldErrors.calle = ACTUACION_VALIDATION_MESSAGES.calleRequerida;
      }

      if (!trim(form.rubro_nombre)) {
        fieldErrors.rubro_nombre = ACTUACION_VALIDATION_MESSAGES.rubroRequerido;
      }
    }
  }

  if (sharedRules && visitaRealizada && !tieneContraproducencia && context.canEditContribuyente !== false) {
    if (!hasTitularPersonaOrazonSocial(form)) {
      fieldErrors.contrib_apellido = ACTUACION_VALIDATION_MESSAGES.titularRequerido;
    }

    const docError = validateDocNro(form.doc_nro);
    if (docError) {
      fieldErrors.doc_nro = docError;
    }

    const inspectoresCount = buildInspectoresForCanal(form as IActuacionListItem).length;
    if (inspectoresCount < 2) {
      fieldErrors.inspectores = ACTUACION_VALIDATION_MESSAGES.inspectoresMinimoDos;
    }
  }

  if (sharedRules) {
    validateCrudActaNumeros(fieldErrors, form);
  }

  if (!visitaRealizada && !contra) {
    fieldErrors.contraproducencia = ACTUACION_VALIDATION_MESSAGES.contraproducenciaVisitaNoRealizada;
  }

  const actaComprobacion = trim(form.acta_comprobacion_num);
  const comprobacionMotivo = trim(form.comprobacion_motivo);
  const actaInspeccion = trim(form.acta_inspeccion_num);
  const actaNotificacion = trim(form.acta_notificacion_num);

  if (completarRules && visitaRealizada && !tieneContraproducencia && !actaInspeccion && !actaComprobacion) {
    fieldErrors.acta_inspeccion_num = ACTUACION_VALIDATION_MESSAGES.actaInspeccionOComprobacionRequerida;
  }

  if (!lockedComp) {
    if (visitaRealizada && actaComprobacion && !comprobacionMotivo) {
      fieldErrors.comprobacion_motivo = ACTUACION_VALIDATION_MESSAGES.comprobacionMotivoSiHayActa;
    }
    if (esNoPermiteInspeccion) {
      const msg = ACTUACION_VALIDATION_MESSAGES.comprobacionNoPermiteInspeccion;
      if (!actaComprobacion) {
        fieldErrors.acta_comprobacion_num = msg;
      }
      if (!comprobacionMotivo) {
        fieldErrors.comprobacion_motivo = msg;
      }
    }
  }

  if (esCorrectivaRubroContraproducencia(contra) && !trim(form.rubro_nombre)) {
    fieldErrors.rubro_nombre = ACTUACION_VALIDATION_MESSAGES.rubroCorrectiva;
  }

  if (esCorrectivaDireccionContraproducencia(contra)) {
    if (!trim(form.calle)) {
      fieldErrors.calle = ACTUACION_VALIDATION_MESSAGES.calleCorrectiva;
    }
    if (!trim(form.numero)) {
      if (omitNumero) {
        warnings.push(ACTUACION_VALIDATION_MESSAGES.numeroNormalizadorWarning);
      } else {
        fieldErrors.numero = ACTUACION_VALIDATION_MESSAGES.numeroCorrectiva;
      }
    }
  }

  if (!lockedNotif && visitaRealizada && !skipNotifRules) {
    const motivos = motivosNotificacionFromSlots(
      form.notificacion_motivo_1,
      form.notificacion_motivo_2,
      form.notificacion_motivo_3
    );
    if (actaNotificacion && motivos.length === 0) {
      fieldErrors.notificacion_motivo_1 = ACTUACION_VALIDATION_MESSAGES.notificacionMotivo;
    }
    if (sharedRules && actaNotificacion && !actaInspeccion) {
      fieldErrors.acta_inspeccion_num = ACTUACION_VALIDATION_MESSAGES.notificacionRequiereInspeccion;
    }
  }

  const decomisoKilos = form.decomiso_kilos_total;
  if (
    decomisoKilos != null &&
    decomisoKilos !== "" &&
    (typeof decomisoKilos !== "number" || Number.isNaN(decomisoKilos))
  ) {
    fieldErrors.decomiso_kilos_total = ACTUACION_VALIDATION_MESSAGES.kilosNumericos;
  }

  const globalError = buildActuacionFormGlobalError(fieldErrors, warnings);

  return {
    fieldErrors,
    globalError,
    warnings,
    canSubmit: Object.keys(fieldErrors).length === 0,
  };
}

/** Contexto por defecto para el CRUD de Actuaciones (modal detalle). */
export function actuacionCrudValidationContext(
  row: IActuacionListItem,
  opts?: { originalRow?: IActuacionListItem | null }
): ActuacionFormValidationContext {
  const editable = getActuacionEditableFields(row);
  const hadContra = Boolean(String(opts?.originalRow?.contraproducencia ?? "").trim());
  const clearingContra = hadContra && !String(row.contraproducencia ?? "").trim();

  return {
    includeCrudEditRules: true,
    includeSharedFormRules: true,
    includeCompletarTrabajoRules: clearingContra,
    visitaRealizada: clearingContra ? true : undefined,
    canEditContribuyente: editable.canEditContribuyente,
    canEditDomicilio: editable.canEditDomicilio,
    omitNumeroManual: false,
    notificacionEditable: editable.canEditNotificacion && row.notificacion_editable !== false,
    comprobacionEditable: row.comprobacion_editable !== false,
    skipNotificacionActaRules: isReinspeccionPorNotificacion(row) || !editable.canEditNotificacion,
  };
}

/** Contexto por defecto para Completar trabajo (formulario de cierre). */
export function actuacionCompletarTrabajoValidationContext(
  visitaRealizada: boolean,
  esReinspeccionNotificacion: boolean
): ActuacionFormValidationContext {
  return {
    source: "completarTrabajo",
    includeCrudEditRules: false,
    includeSharedFormRules: true,
    includeCompletarTrabajoRules: true,
    visitaRealizada,
    omitNumeroManual: false,
    skipNotificacionActaRules: esReinspeccionNotificacion,
  };
}

// Re-export para tests y mensajes de documento/acta.
export { ACTUACION_ACTA_NUM_INVALID_MSG, ACTUACION_DOC_NRO_INVALID_MSG };
