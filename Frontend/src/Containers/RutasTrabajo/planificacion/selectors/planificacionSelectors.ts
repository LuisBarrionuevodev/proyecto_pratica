import type { IPlanificacionPendiente } from "../types/planificacion.types";
import type { PlanificacionCardKey } from "../types/planificacion.types";

/** Tipos “oficio” alineados al backend (card Oficios urgentes / métricas). */
export const TIPOS_OFICIO_PLANIFICACION: readonly string[] = [
  "REINSPECCION_OFICIO",
  "VERIFICAR_INFORMAR_OFICIO",
  "RATIFICACION_CLAUSURA_OFICIO",
  "RATIFICACION_DECOMISO_OFICIO",
];

export function toPoolSet(poolIniciadorIds: number[]): Set<number> {
  return new Set(poolIniciadorIds);
}

export function sinPool<T extends { id: number }>(rows: T[], pool: Set<number>): T[] {
  return rows.filter((r) => !pool.has(r.id));
}

export function aplicarCardContextoLista(
  rows: IPlanificacionPendiente[],
  cardActiva: PlanificacionCardKey
): IPlanificacionPendiente[] {
  if (cardActiva == null) {
    return rows;
  }
  if (cardActiva === "ALTA_PRIORIDAD") {
    return rows.filter((r) => (r.prioridad ?? 0) >= 3);
  }
  if (cardActiva === "OFICIOS_URGENTES") {
    return rows.filter((r) => TIPOS_OFICIO_PLANIFICACION.includes(r.tipo_iniciador));
  }
  if (cardActiva === "DENUNCIAS") {
    return rows.filter((r) => r.tipo_iniciador === "DENUNCIA");
  }
  if (cardActiva === "NOTIFICACIONES") {
    return rows.filter((r) => r.tipo_iniciador === "REINSPECCION_NOTIFICACION");
  }
  if (cardActiva === "RELEVAMIENTOS") {
    return rows.filter((r) => r.tipo_iniciador === "RELEVAMIENTO");
  }
  return rows;
}

/** Orden operativo: prioridad desc, fecha asc, id asc. */
export function ordenarPendientes(rows: IPlanificacionPendiente[]): IPlanificacionPendiente[] {
  return [...rows].sort((a, b) => {
    const pa = a.prioridad ?? 0;
    const pb = b.prioridad ?? 0;
    if (pb !== pa) return pb - pa;
    const fa = a.fecha_origen ?? "";
    const fb = b.fecha_origen ?? "";
    if (fa !== fb) return fa.localeCompare(fb);
    return a.id - b.id;
  });
}
