import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

/**
 * Asegura coherencia de `source_type` en la bandeja de gestión de notificación (GET con
 * `source_type=notificacion`). El backend ya clasifica NOTIFICACION en actuaciones mixtas;
 * este paso corrige respuestas anómalas donde la fila llegue como COMPROBACION pese a tener
 * notificación persistida (no debe ocultar el circuito de plazo frente a la comprobación).
 */
export function normalizeNotificacionBandejaItems(
  items: IActuacionesPendientesItem[],
  metaSourceType?: string | null
): IActuacionesPendientesItem[] {
  const ch = (metaSourceType ?? "").toLowerCase();
  if (ch !== "notificacion") return items;
  return items.map((r) => {
    if (r.source_type === "NOTIFICACION") return r;
    const hasNotiId = r.notificacion_id != null && Number(r.notificacion_id) > 0;
    const hasNotiActa = String(r.acta_notificacion_num ?? "").trim().length > 0;
    if (r.source_type === "COMPROBACION" && (hasNotiId || hasNotiActa)) {
      return { ...r, source_type: "NOTIFICACION" };
    }
    return r;
  });
}
