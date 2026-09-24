import type { IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import { tipoIniciadorDesdeCodigoApi, tipoIniciadorEtiquetaOperativa } from "../planificacion/utils/iniciadorDisplay";

/**
 * Texto de domicilio para Asignación / mapa: prioriza snapshot del ítem (`GET` detail);
 * si falta, enriquece con la fila del pool de planificación (misma sesión).
 */
export function etiquetaDomicilioDesdeItemYPool(item: IRutaItemMin, poolRow?: IRutaIniciadorPendienteRow): string {
  const fromItem = item.domicilio_texto?.trim();
  if (fromItem) return fromItem;
  const fromPoolTexto = poolRow?.domicilio_texto?.trim();
  if (fromPoolTexto) return fromPoolTexto;
  const calleNum = `${poolRow?.domicilio?.calle ?? ""} ${poolRow?.domicilio?.numero ?? ""}`.trim();
  if (calleNum) return calleNum;
  return "Sin domicilio en datos";
}

/**
 * Rubro operativo: ítem (backend) primero; pool como respaldo.
 */
export function rubroOperativoDesdeItemYPool(item: IRutaItemMin, poolRow?: IRutaIniciadorPendienteRow): string {
  const fromItem = item.rubro_nombre?.trim();
  if (fromItem) return fromItem;
  const fromPool = poolRow?.rubro_nombre?.trim() || poolRow?.domicilio?.rubro?.trim();
  if (fromPool) return fromPool;
  return "Sin rubro";
}

/**
 * Distrito para subtítulo: ítem primero; pool como respaldo.
 */
export function distritoOperativoDesdeItemYPool(item: IRutaItemMin, poolRow?: IRutaIniciadorPendienteRow): string | null {
  const fromItem = item.distrito_nombre?.trim();
  if (fromItem) return fromItem;
  const fromPool = poolRow?.distrito_nombre?.trim() || poolRow?.domicilio?.distrito_nombre?.trim();
  if (fromPool) return fromPool;
  return null;
}

/**
 * Etiqueta de tipo: `tipo_iniciador` en ítem (API); si falta, fila del pool (`badges` / código).
 */
export function tipoEtiquetaDesdeItemYPool(item: IRutaItemMin, poolRow?: IRutaIniciadorPendienteRow): string {
  const desdeItem = tipoIniciadorDesdeCodigoApi(item.tipo_iniciador ?? null);
  if (desdeItem) return desdeItem;
  return tipoIniciadorEtiquetaOperativa(poolRow) ?? "SIN TIPO";
}
