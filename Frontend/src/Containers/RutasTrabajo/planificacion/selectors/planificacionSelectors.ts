import type { IPlanificacionPendiente, PlanificacionFiltrosLista } from "../types/planificacion.types";
import type { IPlanificacionMetricas, PlanificacionCardKey } from "../types/planificacion.types";
import { parseIniciadorLatLng } from "../utils/iniciadorCoords";

/** Tipos “oficio” alineados al backend (card Oficios / métricas). */
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

/**
 * Filas M3 visibles en bandeja Urgentes (global).
 * Backend excluye no agregables (OPER-RUTA.6J); aquí se ocultan ítems del pool local al instante (OPER-RUTA.7F.1).
 */
export function filtrarUrgentesVisibles<T extends { id: number }>(rows: T[], pool: Set<number>): T[] {
  return sinPool(rows, pool);
}

/** Filas con geocode válido (mismo criterio que capa de pins del mapa). */
export function filasConPinMapa<T extends IPlanificacionPendiente>(rows: T[]): T[] {
  return rows.filter((r) => parseIniciadorLatLng(r) != null);
}

/**
 * Filtra el dataset del mapa según la KPI card activa (STAB-10c-REWORK).
 * Misma clasificación que `computeMetricasCardsDesdeMapa`.
 */
export function filtrarPendientesMapaPorCard(
  rows: IPlanificacionPendiente[],
  cardActiva: PlanificacionCardKey
): IPlanificacionPendiente[] {
  if (cardActiva == null) {
    return rows;
  }
  if (cardActiva === "ALTA_PRIORIDAD") {
    return rows.filter((r) => r.tipo_iniciador !== "RELEVAMIENTO" && (r.prioridad ?? 0) >= 3);
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

/** @deprecated Usar `filtrarPendientesMapaPorCard`. */
export const aplicarCardContextoLista = filtrarPendientesMapaPorCard;

/** KPIs desde pins visibles en mapa (sin filtro de card activa). */
export function computeMetricasCardsDesdeMapa(rows: IPlanificacionPendiente[]): IPlanificacionMetricas {
  return {
    total: rows.length,
    alta: rows.filter((r) => r.tipo_iniciador !== "RELEVAMIENTO" && (r.prioridad ?? 0) >= 3).length,
    oficios_urgentes: rows.filter((r) => TIPOS_OFICIO_PLANIFICACION.includes(r.tipo_iniciador)).length,
    denuncias: rows.filter((r) => r.tipo_iniciador === "DENUNCIA").length,
    notificaciones: rows.filter((r) => r.tipo_iniciador === "REINSPECCION_NOTIFICACION").length,
    relevamientos: rows.filter((r) => r.tipo_iniciador === "RELEVAMIENTO").length,
  };
}

/** @deprecated Usar `computeMetricasCardsDesdeMapa`. */
export const computeMetricasDesdeFilas = computeMetricasCardsDesdeMapa;

/** Nombre de rubro visible en fila (catálogo o legacy string). */
export function nombreRubroRow(row: IPlanificacionPendiente): string {
  return (row.rubro_nombre ?? row.domicilio?.rubro ?? "").trim();
}

/**
 * Filtros panel Pendientes contexto sobre dataset ya cargado (STAB-10d, frontend).
 * Rubro por nombre de catálogo; domicilio por calle/texto.
 */
export function aplicarFiltrosPendientesContexto(
  rows: IPlanificacionPendiente[],
  filtros: PlanificacionFiltrosLista,
  rubroNombrePorId: (id: number) => string | null
): IPlanificacionPendiente[] {
  let out = rows;

  if (filtros.rubro_id != null) {
    const nombreEsperado = rubroNombrePorId(filtros.rubro_id);
    if (nombreEsperado) {
      const n = nombreEsperado.trim().toLowerCase();
      out = out.filter((r) => nombreRubroRow(r).toLowerCase() === n);
    }
  }

  const q = filtros.q.trim().toLowerCase();
  if (q) {
    out = out.filter((r) => {
      const texto = [r.domicilio_texto, r.domicilio?.calle, r.domicilio?.numero]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return texto.includes(q);
    });
  }

  return out;
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
