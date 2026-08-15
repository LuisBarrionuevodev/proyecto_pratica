import type { NotificacionEstadoOperativoPool } from "../Containers/GestionNotificacion/utils/notificacionEstadoOperativo";

export const MENSAJE_BLOQUEO_GESTION_POOL_RUTA =
  "Este pendiente está en pool o ruta. Para gestionarlo, primero sacalo del pool/ruta.";

export type OperRutaPoolFila = {
  iniciador_id?: number | null;
  estado_operativo_pool?: string | null;
  pool_id?: number | null;
  pool_fecha?: string | null;
  pool_estado?: string | null;
  ruta_item_id?: number | null;
  ruta_trabajo_id?: number | null;
  ruta_numero?: number | null;
  ruta_fecha?: string | null;
  ruta_turno?: string | null;
  grupo_id?: number | null;
  grupo_nombre?: string | null;
  ruta_status?: string | null;
  tiene_orden_trabajo?: boolean | null;
};

export type OperRutaRefreshOptions = {
  silent?: boolean;
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

export function estaBloqueadoParaGestionDocumental(row: OperRutaPoolFila): boolean {
  const estado = normalizarEstadoOperativoPool(row.estado_operativo_pool);
  return estado === "en_pool" || estado === "en_ruta_borrador" || estado === "en_ruta_publicada";
}

/** Muestra «Agregar a ruta de trabajo» en pendiente o en_pool. */
export function puedeAgregarARutaDeTrabajo(row: OperRutaPoolFila): boolean {
  if (!filaTieneIniciadorPlanificable(row)) return false;
  const estado = normalizarEstadoOperativoPool(row.estado_operativo_pool);
  return estado === "pendiente" || estado === "en_pool";
}

/** Sacar del pool cuando está EN_POOL sin ítem de ruta. */
export function puedeSacarDelPool(row: OperRutaPoolFila): boolean {
  if (!filaTieneIniciadorPlanificable(row)) return false;
  if (normalizarEstadoOperativoPool(row.estado_operativo_pool) !== "en_pool") return false;
  if (row.ruta_item_id != null) return false;
  return row.pool_id != null;
}

/** Sacar de ruta borrador sin OT (liberar transaccional). */
export function puedeSacarDeRutaPool(row: OperRutaPoolFila): boolean {
  if (!filaTieneIniciadorPlanificable(row)) return false;
  if (normalizarEstadoOperativoPool(row.estado_operativo_pool) !== "en_ruta_borrador") return false;
  if (row.pool_id == null) return false;
  if (row.tiene_orden_trabajo) return false;
  const rutaStatus = (row.ruta_status ?? "").trim().toUpperCase();
  return rutaStatus === "" || rutaStatus === "BORRADOR";
}

export const MENSAJE_GESTIONAR_DESDE_RUTA_TRABAJO = "Gestionar desde Ruta de Trabajo";

export function debeMostrarGestionarDesdeRutaTrabajo(row: OperRutaPoolFila): boolean {
  const estado = normalizarEstadoOperativoPool(row.estado_operativo_pool);
  return estado === "en_ruta_borrador" || estado === "en_ruta_publicada";
}

export function mostrarAccionesOperRutaPool(row: OperRutaPoolFila): boolean {
  return (
    puedeAgregarARutaDeTrabajo(row) || puedeSacarDelPool(row) || puedeSacarDeRutaPool(row)
  );
}

/** @deprecated OPER-RUTA.6 */
export function puedeAgregarAlPool(row: OperRutaPoolFila): boolean {
  return puedeAgregarARutaDeTrabajo(row) && normalizarEstadoOperativoPool(row.estado_operativo_pool) === "pendiente";
}

/** @deprecated OPER-RUTA.6 */
export function puedeAgregarARuta(row: OperRutaPoolFila): boolean {
  return puedeAgregarARutaDeTrabajo(row);
}

/** Pool del día: solo EN_POOL sin ruta_item. */
export function puedeSacarDelPoolPanel(row: {
  estado?: string | null;
  ruta_item_id?: number | null;
}): boolean {
  const estado = (row.estado ?? "").trim().toUpperCase();
  return estado === "EN_POOL" && (row.ruta_item_id == null || row.ruta_item_id === undefined);
}
