import { esFlujoCierreOficio } from "./completarTrabajoTipoIniciadorUi";

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

/** Contribuyente / domicilio editables solo en visitas de origen (relevamiento, denuncia, etc.). */
export function showContribuyenteDomicilioEditableEnCompletarTrabajo(
  tipoIniciador: string | null | undefined
): boolean {
  if (tipoIniciador === "REINSPECCION_NOTIFICACION") return false;
  if (esFlujoCierreOficio(tipoIniciador)) return false;
  return true;
}
