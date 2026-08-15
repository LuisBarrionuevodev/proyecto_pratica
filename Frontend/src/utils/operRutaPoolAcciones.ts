import type { NotificacionEstadoOperativoPool } from "../Containers/GestionNotificacion/utils/notificacionEstadoOperativo";

export type OperRutaPoolFila = {
  iniciador_id?: number | null;
  estado_operativo_pool?: string | null;
};

export function normalizarEstadoOperativoPool(
  value: string | null | undefined
): NotificacionEstadoOperativoPool | "" {
  return (value ?? "").trim().toLowerCase() as NotificacionEstadoOperativoPool | "";
}

export function filaTieneIniciadorPlanificable(row: OperRutaPoolFila): boolean {
  const id = row.iniciador_id;
  return id != null && !Number.isNaN(Number(id)) && Number(id) > 0;
}

/** Muestra «Agregar al pool» solo en estado pendiente con iniciador. */
export function puedeAgregarAlPool(row: OperRutaPoolFila): boolean {
  if (!filaTieneIniciadorPlanificable(row)) return false;
  return normalizarEstadoOperativoPool(row.estado_operativo_pool) === "pendiente";
}

/** Muestra «Agregar a ruta» en pendiente o en_pool. */
export function puedeAgregarARuta(row: OperRutaPoolFila): boolean {
  if (!filaTieneIniciadorPlanificable(row)) return false;
  const estado = normalizarEstadoOperativoPool(row.estado_operativo_pool);
  return estado === "pendiente" || estado === "en_pool";
}

export function mostrarAccionesOperRutaPool(row: OperRutaPoolFila): boolean {
  return puedeAgregarAlPool(row) || puedeAgregarARuta(row);
}
