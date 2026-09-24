import { listRutaPoolDia, type IListRutaPoolDiaParams, type IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";

/** Tamaño de página para listado EN_POOL (debe coincidir con backend típico). */
export const POOL_EN_POOL_PAGE_SIZE = 100;

/** Tope de páginas consecutivas para evitar bucles infinitos (~10.000 filas). */
export const POOL_EN_POOL_MAX_PAGES = 100;

/**
 * Lista todas las filas EN_POOL paginadas hasta `meta.total` o tope de páginas.
 */
export async function fetchRutaPoolDiaEnPoolAll(
  base: Omit<IListRutaPoolDiaParams, "page" | "per_page">
): Promise<IRutaPoolDiaRow[]> {
  const merged: IRutaPoolDiaRow[] = [];
  let page = 1;
  let totalReported = 0;

  while (page <= POOL_EN_POOL_MAX_PAGES) {
    const { items, meta } = await listRutaPoolDia({
      ...base,
      page,
      per_page: POOL_EN_POOL_PAGE_SIZE,
    });
    if (page === 1) totalReported = meta.total;
    merged.push(...(items ?? []));
    if ((items?.length ?? 0) === 0) break;
    if (merged.length >= totalReported) break;
    if ((items?.length ?? 0) < POOL_EN_POOL_PAGE_SIZE) break;
    page += 1;
  }

  return merged;
}
