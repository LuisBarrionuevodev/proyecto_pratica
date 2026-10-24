import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { useCrudDialogScrollContainer } from "../../../components/crudDialog";
import { getMediaDownloadUrl } from "../../../api/mediaApi";
import {
  LAZY_MEDIA_THUMBNAIL_ROOT_MARGIN,
  LazyThumbnailUrlSession,
  type LazyThumbnailUrlPhase,
} from "../utils/lazyThumbnailUrlSession";

type Options = {
  archivoId: number;
  enabled: boolean;
};

type Result = {
  phase: LazyThumbnailUrlPhase;
  thumbUrl: string | null;
  rootRef: RefObject<HTMLDivElement | null>;
  retry: () => void;
};

/**
 * Obtiene la URL firmada de una miniatura solo cuando el tile es visible (IntersectionObserver).
 */
export function useLazyMediaDownloadUrl({ archivoId, enabled }: Options): Result {
  const [phase, setPhase] = useState<LazyThumbnailUrlPhase>("idle");
  const [thumbUrl, setThumbUrl] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const sessionRef = useRef<LazyThumbnailUrlSession | null>(null);
  const dialogScrollRef = useCrudDialogScrollContainer();

  useEffect(() => {
    sessionRef.current = new LazyThumbnailUrlSession(archivoId, getMediaDownloadUrl);
    setPhase("idle");
    setThumbUrl(null);
  }, [archivoId]);

  const syncFromSession = useCallback(() => {
    const session = sessionRef.current;
    if (!session) return;
    setPhase(session.getPhase());
    setThumbUrl(session.getUrl());
  }, []);

  const runOnVisible = useCallback(async () => {
    const session = sessionRef.current;
    if (!session || !enabled) return;
    await session.onVisible();
    syncFromSession();
  }, [enabled, syncFromSession]);

  useEffect(() => {
    if (!enabled) return;
    const el = rootRef.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      void runOnVisible();
      return;
    }

    const scrollRoot = dialogScrollRef?.current ?? null;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          void runOnVisible();
        }
      },
      {
        root: scrollRoot,
        rootMargin: LAZY_MEDIA_THUMBNAIL_ROOT_MARGIN,
        threshold: 0.01,
      }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [enabled, runOnVisible, archivoId, dialogScrollRef]);

  const retry = useCallback(() => {
    void sessionRef.current?.retry().then(() => syncFromSession());
  }, [syncFromSession]);

  return { phase, thumbUrl, rootRef, retry };
};
