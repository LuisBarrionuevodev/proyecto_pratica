import {
  esFlujoCierreOficio,
  esFlujoVerificarInformar,
  esReinspeccionOficioGenerico,
  esVerificarInformarOficio,
} from "./completarTrabajoTipoIniciadorUi";

export type ShowContribDomicilioEditableOpts = {
  tipoActuacionOficio?: string | null;
  realizoNuevaInspeccion?: string;
};

/** Muestra formulario editable de acta/motivos de notificación. */
export function showNotificacionEditableEnCompletarTrabajo(tipoIniciador: string | null | undefined): boolean {
  return tipoIniciador !== "REINSPECCION_NOTIFICACION";
}

/** Muestra bloque readonly de notificación origen. */
export function showNotificacionOrigenReadonlyEnCompletarTrabajo(tipoIniciador: string | null | undefined): boolean {
  return tipoIniciador === "REINSPECCION_NOTIFICACION";
}

/** Actas distintas de notificación (inspección, comprobación, clausura, decomiso). */
export function showActasEstandarEnCompletarTrabajo(_tipoIniciador: string | null | undefined): boolean {
  return true;
}

/**
 * Contribuyente / domicilio editables en visitas de origen y en Verificar e informar con nueva inspección.
 */
export function showContribuyenteDomicilioEditableEnCompletarTrabajo(
  tipoIniciador: string | null | undefined,
  opts?: ShowContribDomicilioEditableOpts
): boolean {
  if (tipoIniciador === "REINSPECCION_NOTIFICACION") return false;
  if (esVerificarInformarOficio(tipoIniciador)) return true;
  if (
    esReinspeccionOficioGenerico(tipoIniciador) &&
    esFlujoVerificarInformar(tipoIniciador, opts?.tipoActuacionOficio) &&
    opts?.realizoNuevaInspeccion === "si"
  ) {
    return true;
  }
  if (esFlujoCierreOficio(tipoIniciador)) return false;
  return true;
}
