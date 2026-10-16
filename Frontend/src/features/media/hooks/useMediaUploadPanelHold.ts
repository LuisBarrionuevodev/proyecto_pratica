import { useEffect, useState } from "react";
import type { MediaQueuedFile } from "../mediaTypes";
import {
  resolveMediaUploadPanelPhase,
  shouldShowMediaUploadPanel,
} from "../utils/mediaUploadPanelVisibility";

const SUCCESS_HOLD_MS = 8000;

/**
 * Mantiene visible el panel tras éxito o corte hasta timeout o nueva carga.
 */
export function useMediaUploadPanelHold(sessionActive: boolean, items: MediaQueuedFile[]) {
  const [holdOutcome, setHoldOutcome] = useState(false);

  useEffect(() => {
    if (sessionActive) {
      setHoldOutcome(false);
      return;
    }
    const phase = resolveMediaUploadPanelPhase(sessionActive, items);
    if (phase === "success") {
      setHoldOutcome(true);
      const t = window.setTimeout(() => setHoldOutcome(false), SUCCESS_HOLD_MS);
      return () => window.clearTimeout(t);
    }
    if (phase === "interrupted") {
      setHoldOutcome(true);
    }
    if (phase === "idle" && items.length === 0) {
      setHoldOutcome(false);
    }
  }, [sessionActive, items]);

  const visible = shouldShowMediaUploadPanel(sessionActive, items, holdOutcome);
  return { visible, clearHold: () => setHoldOutcome(false) };
}
