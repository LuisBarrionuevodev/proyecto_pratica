import type { MediaQueuedFile } from "../mediaTypes";

export type MediaUploadPanelPhase = "idle" | "uploading" | "success" | "interrupted";

export function resolveMediaUploadPanelPhase(
  sessionActive: boolean,
  items: MediaQueuedFile[]
): MediaUploadPanelPhase {
  if (items.length === 0) return "idle";
  const done = items.filter((x) => x.phase === "ready").length;
  const total = items.length;
  const inFlight = items.some(
    (x) => x.phase === "preparing" || x.phase === "uploading" || x.phase === "verifying"
  );
  const hasError = items.some((x) => x.phase === "error");

  if (sessionActive || inFlight) return "uploading";
  if (hasError && done > 0) return "interrupted";
  if (done === total && total > 0) return "success";
  if (hasError) return "interrupted";
  return "idle";
}

/** Muestra el panel durante carga, éxito reciente o corte con fotos ya guardadas. */
export function shouldShowMediaUploadPanel(
  sessionActive: boolean,
  items: MediaQueuedFile[],
  holdOutcome: boolean
): boolean {
  const phase = resolveMediaUploadPanelPhase(sessionActive, items);
  if (phase === "uploading") return true;
  if (phase === "success" || phase === "interrupted") return holdOutcome;
  return false;
}
