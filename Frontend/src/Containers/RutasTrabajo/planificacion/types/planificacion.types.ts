import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";

/** Fila de pendiente alineada al DTO backend (incl. prioridad_categoria, elegible_urgente). */
export type IPlanificacionPendiente = IRutaIniciadorPendienteRow;

export type PlanificacionCardKey =
  | null
  | "ALTA_PRIORIDAD"
  | "OFICIOS_URGENTES"
  | "DENUNCIAS"
  | "NOTIFICACIONES"
  | "RELEVAMIENTOS";

/** Orden M4 (backend `planificacion/pendientes-contexto`). */
export type PlanificacionOrdenM4 =
  | "prioridad"
  | "fecha_asc"
  | "fecha_desc"
  | "prioridad_asc";

/** Filtros panel Pendientes del contexto (aplicación frontend sobre dataset M4). */
export type PlanificacionFiltrosLista = {
  /** Búsqueda por domicilio / calle / texto. */
  q: string;
  rubro_id: number | null;
};

export type UrgentesFiltrosAplicados = {
  tipo_urgente: "" | "DENUNCIA" | "NOTIFICACION" | "OFICIO";
  rubro_id: number | null;
  q_identificador: string;
  q_domicilio: string;
};

export interface IPlanificacionMetricas {
  total: number;
  alta: number;
  oficios_urgentes: number;
  denuncias: number;
  notificaciones: number;
  relevamientos: number;
}

export interface ICargaDistritoRow {
  distrito_id: number;
  distrito_nombre: string;
  cantidad: number;
}
