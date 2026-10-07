import type { MediaQueuedFile } from "../mediaTypes";

export type ManualMediaSaveOutcome = "success" | "partial" | "empty";

export function countUploadableQueueItems(items: MediaQueuedFile[]): number {
  return items.filter(
    (x) => x.phase === "pending" || (x.phase === "error" && x.archivoId == null)
  ).length;
}

/**
 * Guardado manual Mis trabajos: sube cola, limpia READY local y refresca servidor.
 * No lanza por fallo de refresh tras subida exitosa (evita falso error).
 */
export async function runManualMediaSave(params: {
  rutaItemId: number;
  uploadAll: (rutaItemId: number) => Promise<void>;
  getQueueItems: () => MediaQueuedFile[];
  clearUploadedFromQueue: () => void;
  reloadServer: () => Promise<void>;
}): Promise<{ outcome: ManualMediaSaveOutcome; refreshFailed: boolean }> {
  if (countUploadableQueueItems(params.getQueueItems()) === 0) {
    return { outcome: "empty", refreshFailed: false };
  }

  await params.uploadAll(params.rutaItemId);

  const after = params.getQueueItems();
  if (countUploadableQueueItems(after) > 0 || after.some((x) => x.phase === "error")) {
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
