import type { UrgentesFiltrosAplicados } from "../types/planificacion.types";

export type BuildUrgentesQueryParamsInput = {
  page?: number;
  per_page?: number;
  distrito_id?: number | null;
  filtros?: UrgentesFiltrosAplicados;
};

/**
 * Arma query params M3 sin enviar filtros vacíos ni sentinela TODOS.
 */
export function buildUrgentesQueryParams(
  input: BuildUrgentesQueryParamsInput
): Record<string, string | number> {
  const query: Record<string, string | number> = {};

  const page = input.page ?? 1;
  const perPage = input.per_page ?? 25;
  if (page >= 1) query.page = page;
  if (perPage >= 1) query.per_page = perPage;

  if (input.distrito_id != null) {
    query.distrito_id = input.distrito_id;
  }

  const f = input.filtros;
  if (!f) return query;

  const tipo = f.tipo_urgente?.trim();
  if (tipo && tipo !== "TODOS") {
    query.tipo_urgente = tipo;
  }

  if (f.rubro_id != null && f.rubro_id >= 1) {
    query.rubro_id = f.rubro_id;
  }

  const qIdentificador = f.q_identificador?.trim();
  if (qIdentificador) query.q_identificador = qIdentificador;

  const qDomicilio = f.q_domicilio?.trim();
  if (qDomicilio) query.q_domicilio = qDomicilio;

  return query;
}
