import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { isReinspeccionOficioCircuitRow } from "../../../shared/reinspeccionOficio/isReinspeccionOficioCircuitRow";
import { usaInspeccionNormalReinspeccionOficio } from "../../../shared/reinspeccionOficio/usaInspeccionNormalReinspeccionOficio";
import type { VerificarEstadoOperativo } from "../../../shared/reinspeccionOficio/verificarEstadoOperativo";

import {
  isInspeccionIntegralOrDenuncia,
  isRatificacionClausura,
  isRatificacionDecomiso,
  isReinspeccionPorNotificacion,
  isVerificarEInformar,
  tieneClausuraLabrada,
  tieneComprobacionLabrada,
  tieneDecomisoLabrado,
  tieneInspeccionLabrada,
  tieneNotificacionLabradaMotivos,
} from "./actuacionesExportPdfResumen";

/** Mensaje estándar cuando la edición está bloqueada por expediente en notificación/comprobación. */
export const MENSAJE_BLOQUEO_EXPEDIENTE_EDICION =
  "Esta actuación tiene un expediente asociado a una notificación o comprobación. Editá primero esa sección y luego volvé a Actuaciones si necesitás modificar datos generales.";

/** FIX.5 — actuación histórica con intento posterior del mismo iniciador. */
export const MENSAJE_BLOQUEO_INTENTO_POSTERIOR =
  "Esta actuación no puede editarse porque existe un intento posterior asociado al mismo iniciador.";

/** Intento de borrar acta con documentación asociada desde CRUD Actuaciones. */
export const MENSAJE_BLOQUEO_ACTA_DOCUMENTACION =
  "Esta acta tiene documentación asociada y debe modificarse desde la sección correspondiente.";

export type ActuacionModoEdicion =
  | "normal"
  | "reinspeccion_notificacion"
  | "reinspeccion_oficio"
  | "ratificacion"
  | "verificar_informar";

export type ActuacionEditableFields = {
  canEditContribuyente: boolean;
  canEditDomicilio: boolean;
  /** Motivo de bloqueo de domicilio (PR7.15, desde backend). */
  domicilioEditBlockedReason: string | null;
  /** FIX.6 — rubro operativo desacoplado de domicilio (p. ej. Denuncia en corrección). */
  canEditRubro: boolean;
  rubroEditBlockedReason: string | null;
  /** FIX.7 — nombre de fantasía del local. */
  canEditNombreLocal: boolean;
  canEditActas: boolean;
  /** Solo Verificar + SI_INSPECCION en reinspección por oficio; undefined fuera del circuito. */
  usaInspeccionNormal?: boolean;
  /** True cuando debe validarse/completarse acta de inspección normal (≠ mostrar actas para quitar). */
  debeValidarActasInspeccionNormal?: boolean;
  canEditNotificacion: boolean;
  canEditResultadoOperativo: boolean;
  modoEdicion: ActuacionModoEdicion;
};

/**
 * Indica si la actuación tiene expediente asociado que impide editar desde el modal de Actuaciones.
 *
 * Usa flags ya presentes en el detalle/listado (`notificacion_editable`, `comprobacion_editable`).
 */
export function tieneExpedienteBloqueoEdicion(row: IActuacionListItem): boolean {
  return row.notificacion_editable === false || row.comprobacion_editable === false;
}

/** Acta de notificación bloqueada por expediente/documentación. */
export function actaNotificacionBloqueadaEdicion(row: IActuacionListItem): boolean {
  return row.notificacion_editable === false;
}

/** Acta de comprobación bloqueada por expediente/documentación. */
export function actaComprobacionBloqueadaEdicion(row: IActuacionListItem): boolean {
  return row.comprobacion_editable === false;
}

/** Reinspección por oficio genérica (circuito documental, sin subtipo ratificación/verificar). */
function isReinspeccionOficioGenericaEdicion(row: IActuacionListItem): boolean {
  return row.documentacion_contexto?.circuito === "REINSPECCION_OFICIO";
}

/** Actas o datos persistidos del flujo de inspección normal (paridad Completar Trabajo). */
export function tieneActasInspeccionNormalPersistidas(row: IActuacionListItem): boolean {
  return (
    tieneInspeccionLabrada(row) ||
    tieneNotificacionLabradaMotivos(row) ||
    tieneComprobacionLabrada(row) ||
    tieneClausuraLabrada(row) ||
    tieneDecomisoLabrado(row)
  );
}

/**
 * Resuelve el modo de edición CRUD según tipo de actuación / circuito documental.
 */
export function resolveActuacionModoEdicion(row: IActuacionListItem): ActuacionModoEdicion {
  if (isReinspeccionPorNotificacion(row)) return "reinspeccion_notificacion";
  if (isRatificacionClausura(row) || isRatificacionDecomiso(row)) return "ratificacion";
  if (isVerificarEInformar(row)) return "verificar_informar";
  if (isReinspeccionOficioGenericaEdicion(row)) return "reinspeccion_oficio";
  if (isInspeccionIntegralOrDenuncia(row)) return "normal";

  const tipo = String(row.tipo_actuacion ?? "")
    .trim()
    .toUpperCase();
  if (
    tipo === "INSPECCION" ||
    tipo.includes("INSPECCION INTEGRAL") ||
    tipo.includes("DENUNCIA") ||
    tipo.includes("INSPECCION / DENUNCIA")
  ) {
    return "normal";
  }
  return "normal";
}

export type ActaTipoPersistida =
  | "INSPECCION"
  | "NOTIFICACION"
  | "COMPROBACION"
  | "CLAUSURA"
  | "DECOMISO";

/**
 * C — debe mostrar acta persistida para quitar (independiente de crear/validar).
 */
export function debeMostrarActaPersistidaParaQuitar(
  tipo: ActaTipoPersistida,
  row: IActuacionListItem
): boolean {
  switch (tipo) {
    case "INSPECCION":
      return tieneInspeccionLabrada(row);
    case "NOTIFICACION":
      return (
        tieneNotificacionLabradaMotivos(row) || Boolean(String(row.acta_notificacion_num ?? "").trim())
      );
    case "COMPROBACION":
      return (
        tieneComprobacionLabrada(row) || Boolean(String(row.acta_comprobacion_num ?? "").trim())
      );
    case "CLAUSURA":
      return tieneClausuraLabrada(row);
    case "DECOMISO":
      return tieneDecomisoLabrado(row);
    default:
      return false;
  }
}

/** Si el campo de acta debe renderizarse en edición (crear, validar o quitar persistida). */
export function debeMostrarCampoActaEnEdicion(
  tipo: ActaTipoPersistida,
  row: IActuacionListItem,
  fields: ActuacionEditableFields,
  baseline?: IActuacionListItem | null
): boolean {
  if (tipo === "NOTIFICACION" && fields.modoEdicion === "reinspeccion_notificacion") {
    return false;
  }

  const persisted =
    debeMostrarActaPersistidaParaQuitar(tipo, row) ||
    (baseline ? debeMostrarActaPersistidaParaQuitar(tipo, baseline) : false);

  if (fields.modoEdicion === "normal") {
    return true;
  }

  if (fields.modoEdicion === "reinspeccion_notificacion") {
    const destinoRealizado = !trim(row.contraproducencia);
    return destinoRealizado || persisted;
  }

  if (fields.debeValidarActasInspeccionNormal) {
    return true;
  }

  return persisted;
}

function resolveCanEditDomicilio(row: IActuacionListItem, modo: ActuacionModoEdicion): boolean {
  if (row.can_edit_domicilio === true) return true;
  if (row.can_edit_domicilio === false) return false;
  // Fallback sin flag backend (tests locales / datos viejos).
  return modo === "normal";
}

function resolveCanEditRubro(row: IActuacionListItem, modo: ActuacionModoEdicion): boolean {
  if (row.can_edit_rubro === true) return true;
  if (row.can_edit_rubro === false) return false;
  // Fallback sin flag backend: paridad con domicilio en modo normal.
  return resolveCanEditDomicilio(row, modo);
}

export type ActuacionEditableFieldsOptions = {
  /** Estado UI de «¿Realizó nueva inspección?» en edición Verificar (antes de guardar). */
  verificarRealizoNuevaInspeccion?: "" | "si" | "no";
  /** Subtipo destino del formulario Oficio (puede diferir de `row.tipo_actuacion` persistido). */
  oficioSubtipo?: string;
  /** Estado operativo Verificar destino (formulario Oficio). */
  verificarEstadoOperativo?: VerificarEstadoOperativo;
  /** Fila al abrir edición; mantiene bloque Actas aunque el usuario vacíe campos en draft. */
  baselineRow?: IActuacionListItem;
};

/**
 * Permisos de edición por tipo de actuación (paridad operativa con Completar Trabajo).
 */
export function getActuacionEditableFields(
  row: IActuacionListItem,
  options?: ActuacionEditableFieldsOptions
): ActuacionEditableFields {
  const esOficio =
    isReinspeccionOficioCircuitRow(row) || Boolean(options?.oficioSubtipo?.trim());
  const esOficioHardBlock = esOficio;
  const rowForModo =
    esOficio && options?.oficioSubtipo?.trim()
      ? { ...row, tipo_actuacion: options.oficioSubtipo.trim() }
      : row;
  const modo = resolveActuacionModoEdicion(rowForModo);
  const normal = modo === "normal";
  const verificarRealizo =
    options?.verificarRealizoNuevaInspeccion ??
    (row.realizo_nueva_inspeccion === true
      ? "si"
      : row.realizo_nueva_inspeccion === false
        ? "no"
        : "");

  const usaInspeccionNormal = esOficio
    ? usaInspeccionNormalReinspeccionOficio(
        options?.oficioSubtipo ?? row.tipo_actuacion,
        options?.verificarEstadoOperativo ?? ""
      )
    : undefined;

  const verificarRealizoLegacy = modo === "verificar_informar" && !esOficio && verificarRealizo === "si";
  const muestraInspeccionNormalOficio = usaInspeccionNormal === true;
  const tieneActasPersistidas =
    tieneActasInspeccionNormalPersistidas(row) ||
    (options?.baselineRow ? tieneActasInspeccionNormalPersistidas(options.baselineRow) : false);

  const canEditActas =
    normal ||
    modo === "reinspeccion_notificacion" ||
    verificarRealizoLegacy ||
    muestraInspeccionNormalOficio ||
    (esOficio && tieneActasPersistidas);

  const canEditResultadoOperativo =
    modo === "ratificacion" || modo === "verificar_informar" || modo === "reinspeccion_oficio";

  return {
    canEditContribuyente: esOficioHardBlock ? false : normal,
    canEditDomicilio: esOficioHardBlock ? false : resolveCanEditDomicilio(row, modo),
    domicilioEditBlockedReason: row.domicilio_edit_blocked_reason ?? null,
    canEditRubro: esOficioHardBlock ? false : resolveCanEditRubro(row, modo),
    rubroEditBlockedReason: row.rubro_edit_blocked_reason ?? null,
    canEditNombreLocal: esOficioHardBlock ? false : normal,
    canEditActas,
    usaInspeccionNormal,
    debeValidarActasInspeccionNormal: usaInspeccionNormal === true,
    canEditNotificacion:
      (normal || muestraInspeccionNormalOficio) && modo !== "reinspeccion_notificacion",
    canEditResultadoOperativo,
    modoEdicion: modo,
  };
}

export type ActuacionEditStartResult = { allowed: true } | { allowed: false; message: string };

/**
 * Resuelve si el modal puede pasar a modo edición al presionar «Editar».
 *
 * @param row Fila/detalle actual de la actuación.
 * @returns `{ allowed: true }` o bloqueo con mensaje de advertencia.
 */
export function resolveActuacionEditStart(row: IActuacionListItem): ActuacionEditStartResult {
  if (row.actuacion_editable === false) {
    return {
      allowed: false,
      message: row.motivo_bloqueo_edicion?.trim() || MENSAJE_BLOQUEO_INTENTO_POSTERIOR,
    };
  }
  if (tieneExpedienteBloqueoEdicion(row)) {
    return { allowed: false, message: MENSAJE_BLOQUEO_EXPEDIENTE_EDICION };
  }
  return { allowed: true };
}

function trim(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * Detecta intento de borrar acta bloqueada por documentación asociada.
 *
 * @param draft Borrador actual del modal.
 * @param baseline Fila al abrir edición (antes de cambios).
 * @returns Mensaje de warning o null si no aplica.
 */
export function detectBlockedActaClearAttempt(
  draft: IActuacionListItem,
  baseline: IActuacionListItem
): string | null {
  if (
    actaNotificacionBloqueadaEdicion(baseline) &&
    trim(baseline.acta_notificacion_num) &&
    !trim(draft.acta_notificacion_num)
  ) {
    return MENSAJE_BLOQUEO_ACTA_DOCUMENTACION;
  }
  if (
    actaComprobacionBloqueadaEdicion(baseline) &&
    trim(baseline.acta_comprobacion_num) &&
    !trim(draft.acta_comprobacion_num)
  ) {
    return MENSAJE_BLOQUEO_ACTA_DOCUMENTACION;
  }
  return null;
}
