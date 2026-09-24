/**
 * Medición temporal de performance en el front (QA).
 *
 * Activar con `VITE_PERF_LOG=1` en `.env.local`.
 * Sin flag: no-op (cero logs).
 */

function perfEnabled(): boolean {
  const v = import.meta.env.VITE_PERF_LOG;
  return v === "1" || v === "true" || v === "yes";
}

/** Log informativo bajo flag de performance. */
export function perfLog(label: string, data: Record<string, unknown>): void {
  if (!perfEnabled()) return;
  console.info(`[perf] ${label}`, data);
}

/** Mide tiempo de una promesa y registra el resultado. */
export async function perfTimed<T>(
  label: string,
  fn: () => Promise<T>,
  extra?: (result: T) => Record<string, unknown>
): Promise<T> {
  const t0 = performance.now();
  const result = await fn();
  perfLog(label, {
    ms: Math.round(performance.now() - t0),
    ...(extra ? extra(result) : {}),
  });
  return result;
}
