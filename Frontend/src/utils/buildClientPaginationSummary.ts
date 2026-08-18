export const DEFAULT_BANDEJA_CLIENT_PAGE_SIZE = 10;

export type ClientPaginationSummaryInput = {
  pageIndex: number;
  pageSize: number;
  totalRows: number;
};

export type ClientPaginationSummary = {
  currentPage: number;
  totalPages: number;
  visibleRows: number;
  totalRows: number;
};

/**
 * Resumen de paginación client-side (MRT) para barra Total / Mostrando / Página.
 */
export function buildClientPaginationSummary({
  pageIndex,
  pageSize,
  totalRows,
}: ClientPaginationSummaryInput): ClientPaginationSummary {
  const safePageSize = Math.max(1, pageSize);
  const totalPages = Math.max(1, Math.ceil(totalRows / safePageSize) || 1);
  const currentPage = Math.min(pageIndex + 1, totalPages);
  if (totalRows <= 0) {
    return { currentPage: 1, totalPages: 1, visibleRows: 0, totalRows: 0 };
  }
  const start = pageIndex * safePageSize;
  const visibleRows = Math.min(safePageSize, Math.max(0, totalRows - start));
  return { currentPage, totalPages, visibleRows, totalRows };
}

/** Resetea a página 1 conservando pageSize elegido por el usuario. */
export function resetClientPaginationPageIndex<T extends { pageIndex: number; pageSize: number }>(
  prev: T
): T {
  return { ...prev, pageIndex: 0 };
}
