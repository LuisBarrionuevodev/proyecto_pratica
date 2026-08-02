import type { ActuacionesExportFilters } from "../../../api/actuacionesExportApi";
import type { IActuacionesListFilters, IActuacionesListMeta } from "../../../api/actuacionesListApi";

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

/**
 * Arma filtros del export dataset alineados al universo visible en la bandeja.
 *
 * - Con `q` activo en meta, replica exactamente los filtros del listado (sin período del diálogo).
 * - Sin `q`, usa el rango elegido en el diálogo de exportación más catálogos de meta.
 */
export function buildActuacionesExportFiltersFromMeta(
  meta: IActuacionesListMeta,
  dialogRange?: { desde: string; hasta: string }
): ActuacionesExportFilters {
  if (meta.q) {
    return {
      q: meta.q,
      desde: meta.desde ?? null,
      hasta: meta.hasta ?? null,
      tipo: meta.tipo,
      contraproducencia: meta.contraproducencia,
      orden_trabajo: meta.orden_trabajo,
    };
  }

  return {
    q: null,
    desde: dialogRange?.desde ?? meta.desde,
    hasta: dialogRange?.hasta ?? meta.hasta,
    tipo: meta.tipo,
    contraproducencia: meta.contraproducencia,
    orden_trabajo: meta.orden_trabajo,
  };
}
