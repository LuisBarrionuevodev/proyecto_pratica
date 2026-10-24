import type { MediaQueuedFile } from "../mediaTypes";

/**
 * Aplica un patch a un ítem de cola sin degradar un estado READY terminal (MEDIA.2E.1B).
 */
export function mergeMediaQueueItemPatch(
  existing: MediaQueuedFile,
  patch: Partial<MediaQueuedFile>
): MediaQueuedFile {
  if (existing.phase === "ready") {
    const nextPhase = patch.phase;
    if (nextPhase != null && nextPhase !== "ready") {
      return existing;
    }
    const safe: Partial<MediaQueuedFile> = { ...patch };
    delete safe.phase;
    delete safe.errorMessage;
    delete safe.progressPct;
    return { ...existing, ...safe };
  }
  return { ...existing, ...patch };
}
