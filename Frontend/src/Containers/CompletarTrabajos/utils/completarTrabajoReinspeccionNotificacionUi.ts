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

type NotificacionOrigenRow = {
  acta_notificacion_num?: string | null;
  notificacion_origen_texto?: string | null;
  notificacion_origen_anio?: number | null;
};

/** Texto readonly de notificación origen para reinspección por notificación. */
export function formatNotificacionOrigenReadonly(row: NotificacionOrigenRow | null | undefined): string {
  const texto = (row?.notificacion_origen_texto ?? "").trim();
  if (texto) return texto;
  const num = (row?.acta_notificacion_num ?? "").trim();
  if (!num) return "";
  const anio = row?.notificacion_origen_anio;
  return anio != null ? `${num}/${anio}` : num;
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
