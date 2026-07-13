import type { IActuacionesListFilters } from "../../../api/actuacionesListApi";

export interface ActuacionesFiltroFormState {
  desde: string;
  hasta: string;
  tipo: string;
  contraproducencia: string;
  /** Búsqueda específica (acta, domicilio, expediente, oficio…). */
  busquedaEspecifica: string;
  /** Si true, la búsqueda específica también respeta rango y filtros de catálogo. */
  combinarConRango: boolean;
}

const MIN_Q_LENGTH = 2;

/**
 * Arma el payload del listado separando búsqueda por rango y búsqueda específica.
 *
 * - Con texto específico (≥2 caracteres) y sin «combinar», no envía fechas ni catálogos
 *   para evitar que un rango viejo limite resultados accidentales.
 * - Con solo rango/catálogos, aplica fechas y filtros de tipo/contraproducencia.
 */
export function buildActuacionesFiltroPayload(
  form: ActuacionesFiltroFormState
): IActuacionesListFilters {
  const q = form.busquedaEspecifica.trim();
  const isSpecificSearch = q.length >= MIN_Q_LENGTH;
  const useRangeModifiers = !isSpecificSearch || form.combinarConRango;

  return {
    desde: useRangeModifiers ? form.desde || null : null,
    hasta: useRangeModifiers ? form.hasta || null : null,
    tipo: useRangeModifiers ? form.tipo || null : null,
    contraproducencia: useRangeModifiers ? form.contraproducencia || null : null,
    orden_trabajo: null,
    actuacion_id: null,
    q: isSpecificSearch ? q : null,
  };
}

export function actuacionesBusquedaEspecificaValida(texto: string): boolean {
  return texto.trim().length >= MIN_Q_LENGTH;
}

export const ACTUACIONES_BUSQUEDA_ESPECIFICA_MIN_CHARS = MIN_Q_LENGTH;
