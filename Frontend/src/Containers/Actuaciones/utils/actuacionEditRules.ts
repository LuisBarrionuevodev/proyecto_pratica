import type { IActuacionListItem } from "../../../api/actuacionesListApi";

import {

  isInspeccionIntegralOrDenuncia,

  isRatificacionClausura,

  isRatificacionDecomiso,

  isReinspeccionPorNotificacion,

  isVerificarEInformar,

} from "./actuacionesExportPdfResumen";



/** Mensaje estándar cuando la edición está bloqueada por expediente en notificación/comprobación. */

export const MENSAJE_BLOQUEO_EXPEDIENTE_EDICION =

  "Esta actuación tiene un expediente asociado a una notificación o comprobación. Editá primero esa sección y luego volvé a Actuaciones si necesitás modificar datos generales.";



/** Intento de borrar acta con documentación asociada desde CRUD Actuaciones. */

export const MENSAJE_BLOQUEO_ACTA_DOCUMENTACION =

  "Esta acta tiene documentación asociada y debe modificarse desde la sección correspondiente.";



export type ActuacionModoEdicion =

  | "normal"

  | "reinspeccion_notificacion"

  | "ratificacion"

  | "verificar_informar";



export type ActuacionEditableFields = {

  canEditContribuyente: boolean;

  canEditDomicilio: boolean;

  canEditActas: boolean;

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



/**

 * Resuelve el modo de edición CRUD según tipo de actuación / circuito documental.

 */

export function resolveActuacionModoEdicion(row: IActuacionListItem): ActuacionModoEdicion {

  if (isReinspeccionPorNotificacion(row)) return "reinspeccion_notificacion";

  if (isRatificacionClausura(row) || isRatificacionDecomiso(row)) return "ratificacion";

  if (isVerificarEInformar(row)) return "verificar_informar";

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



/**

 * Permisos de edición por tipo de actuación (paridad operativa con Completar Trabajo).

 */

export function getActuacionEditableFields(row: IActuacionListItem): ActuacionEditableFields {

  const modo = resolveActuacionModoEdicion(row);

  const normal = modo === "normal";

  const reinspeccionNotif = modo === "reinspeccion_notificacion";



  return {

    canEditContribuyente: normal,

    canEditDomicilio: normal || reinspeccionNotif,

    canEditActas: true,

    canEditNotificacion: normal,

    canEditResultadoOperativo: !normal,

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


