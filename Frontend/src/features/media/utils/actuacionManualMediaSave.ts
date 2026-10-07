import type { MediaQueuedFile } from "../mediaTypes";

export type ManualMediaSaveOutcome = "success" | "partial" | "empty";

export function countUploadableQueueItems(items: MediaQueuedFile[]): number {
  return items.filter(
    (x) => x.phase === "pending" || (x.phase === "error" && x.archivoId == null)
  ).length;
}

/** True si quedó algún archivo de la cola que no terminó READY tras el pipeline. */
export function hasIncompleteUploadInQueue(items: MediaQueuedFile[]): boolean {
  return items.some(
    (x) =>
      x.phase === "pending" ||
      x.phase === "preparing" ||
      x.phase === "uploading" ||
      x.phase === "verifying" ||
      x.phase === "error"
  );
}

export type ManualMediaSaveResult = {
  outcome: ManualMediaSaveOutcome;
  refreshFailed: boolean;
};

/**
 * Guardado manual Mis trabajos: sube cola, limpia READY local y refresca servidor.
 * El refresh fallido no convierte un upload exitoso en `partial`.
 */
export async function runManualMediaSave(params: {
  rutaItemId: number;
  uploadAll: (rutaItemId: number) => Promise<void>;
  getQueueItems: () => MediaQueuedFile[];
  clearUploadedFromQueue: () => void;
  reloadServer: () => Promise<void>;
}): Promise<ManualMediaSaveResult> {
  if (countUploadableQueueItems(params.getQueueItems()) === 0) {
    return { outcome: "empty", refreshFailed: false };
  }

  await params.uploadAll(params.rutaItemId);

  const afterUpload = params.getQueueItems();
  if (hasIncompleteUploadInQueue(afterUpload)) {
    return { outcome: "partial", refreshFailed: false };
  }

  params.clearUploadedFromQueue();

  let refreshFailed = false;
  try {
    await params.reloadServer();
  } catch {
    refreshFailed = true;
  }
  return { outcome: "success", refreshFailed };
}

/** Cierra el modal de fotos Inspector solo tras éxito operativo de subida. */
export function shouldCloseInspectorFotosModalAfterSave(outcome: ManualMediaSaveOutcome): boolean {
  return outcome === "success";
}
