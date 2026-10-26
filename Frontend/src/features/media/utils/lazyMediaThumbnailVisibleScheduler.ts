type VisibleRunner = () => void;

let rafHandle: number | null = null;
const queuedRunners = new Map<number, VisibleRunner>();

/**
 * Agrupa callbacks de visibilidad de miniaturas en un único `requestAnimationFrame` (PERF.6).
 */
export function scheduleLazyThumbnailVisible(archivoId: number, run: VisibleRunner): void {
  if (queuedRunners.has(archivoId)) return;
  queuedRunners.set(archivoId, run);
  if (rafHandle != null) return;
  rafHandle = requestAnimationFrame(() => {
    rafHandle = null;
    const runners = [...queuedRunners.values()];
    queuedRunners.clear();
    for (const runner of runners) {
      runner();
    }
  });
}

/** Solo tests: ejecuta la cola pendiente sin esperar al siguiente frame. */
export function flushLazyThumbnailVisibleQueueForTests(): void {
  if (rafHandle != null && typeof cancelAnimationFrame === "function") {
    cancelAnimationFrame(rafHandle);
    rafHandle = null;
  }
  const runners = [...queuedRunners.values()];
  queuedRunners.clear();
  for (const runner of runners) {
    runner();
  }
}

/** Solo tests: reinicia estado del scheduler. */
export function resetLazyThumbnailVisibleSchedulerForTests(): void {
  if (rafHandle != null && typeof cancelAnimationFrame === "function") {
    cancelAnimationFrame(rafHandle);
  }
  rafHandle = null;
  queuedRunners.clear();
}
