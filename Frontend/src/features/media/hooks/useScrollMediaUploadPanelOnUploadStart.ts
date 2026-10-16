import { useEffect, useRef, type RefObject } from "react";
import { scheduleScrollMediaUploadPanelIntoView } from "../utils/scrollMediaUploadPanelIntoView";

/**
 * Al iniciar una carga (flanco activo → true), hace scroll al panel sin mover foco de inputs.
 */
export function useScrollMediaUploadPanelOnUploadStart(
  uploadActive: boolean,
  panelVisible: boolean,
  panelRef: RefObject<HTMLElement | null>,
  scrollContainerRef?: RefObject<HTMLElement | null> | null
): void {
  const prevUploadActiveRef = useRef(false);

  useEffect(() => {
    const started = uploadActive && !prevUploadActiveRef.current;
    prevUploadActiveRef.current = uploadActive;
    if (!started || !panelVisible) return;
    scheduleScrollMediaUploadPanelIntoView(
      panelRef.current,
      scrollContainerRef?.current ?? null
    );
  }, [uploadActive, panelVisible, panelRef, scrollContainerRef]);
}
