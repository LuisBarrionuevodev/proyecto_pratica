/** Evento interno: recargar tab «Pendiente reinspección» tras cerrar REINSPECCION_NOTIFICACION. */
export const GESTION_NOTIF_REINSPECCION_REFRESH_EVENT = "gestion-notif:reinspeccion-refresh";

export function emitGestionNotificacionReinspeccionRefresh(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(GESTION_NOTIF_REINSPECCION_REFRESH_EVENT));
}

export function subscribeGestionNotificacionReinspeccionRefresh(listener: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(GESTION_NOTIF_REINSPECCION_REFRESH_EVENT, listener);
  return () => window.removeEventListener(GESTION_NOTIF_REINSPECCION_REFRESH_EVENT, listener);
}
