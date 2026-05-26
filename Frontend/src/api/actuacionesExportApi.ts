import type { IActuacionListItem, IActuacionesListFilters } from "./actuacionesListApi";
import { getActuacionesFiltered } from "./actuacionesListApi";

const EXPORT_PAGE_SIZE = 500;

export type ActuacionesExportFilters = Pick<
  IActuacionesListFilters,
  "desde" | "hasta" | "tipo" | "contraproducencia" | "orden_trabajo"
>;

export type FetchAllActuacionesProgress = {
  loaded: number;
  total: number;
  page: number;
};

/**
 * Obtiene todas las actuaciones del rango/filtros iterando páginas hasta `meta.total`.
 * No depende de la página visible en la grilla.
 */
export async function fetchAllActuacionesForExport(
  filters: ActuacionesExportFilters,
  onProgress?: (progress: FetchAllActuacionesProgress) => void
): Promise<IActuacionListItem[]> {
  const all: IActuacionListItem[] = [];
  let page = 1;
  let total = 0;

  for (;;) {
    const response = await getActuacionesFiltered({
      ...filters,
      page,
      page_size: EXPORT_PAGE_SIZE,
    });

    total = response.meta.total;
    all.push(...response.items);

    onProgress?.({ loaded: all.length, total, page });

    if (response.items.length === 0 || all.length >= total) {
      break;
    }
    page += 1;
  }

  return all;
}
