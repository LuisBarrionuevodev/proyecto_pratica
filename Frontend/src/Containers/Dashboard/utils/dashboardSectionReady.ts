/**
 * Indica si un bloque del dashboard ya resolvió (datos o error).
 */
export function isDashboardSectionReady<T>(
  data: T | null | undefined,
  error: string | null | undefined
): boolean {
  return data != null || Boolean(error);
}
