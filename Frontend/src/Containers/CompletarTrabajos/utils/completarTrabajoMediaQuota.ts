import type { MediaCategoria } from "../../../features/media/mediaConstants";
import { MEDIA_CATEGORY_MAX } from "../../../features/media/mediaConstants";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";

export type MediaQuotaAddResult = {
  accepted: File[];
  added: number;
  skipped: number;
  quotaFull: boolean;
};

/**
 * Recorta una selección al cupo disponible (READY en servidor + cola local válida).
 */
export function sliceFilesToAvailableQuota(
  files: File[],
  categoria: MediaCategoria,
  serverReadyCount: number,
  localItems: MediaQueuedFile[]
): MediaQuotaAddResult {
  const max = MEDIA_CATEGORY_MAX[categoria];
  const localActive = localItems.filter(
    (x) => x.categoria === categoria && x.phase !== "error"
  ).length;
  let available = max - serverReadyCount - localActive;
  if (available <= 0) {
    return { accepted: [], added: 0, skipped: files.length, quotaFull: true };
  }
  const accepted = files.slice(0, available);
  const skipped = files.length - accepted.length;
  return {
    accepted,
    added: accepted.length,
    skipped,
    quotaFull: skipped > 0 && available <= files.length,
  };
}
