import type { MediaArchivoListItem } from "../mediaTypes";

export type MediaPreviewNavState = {
  showNav: boolean;
  counter: string | null;
  index: number;
  canGoPrevious: boolean;
  canGoNext: boolean;
};

export function findPreviewItemIndex(
  items: MediaArchivoListItem[],
  archivoId: number | null
): number {
  if (archivoId == null) return -1;
  return items.findIndex((i) => i.archivo_id === archivoId);
}

export function getMediaPreviewNavState(
  items: MediaArchivoListItem[],
  archivoId: number | null
): MediaPreviewNavState {
  const index = findPreviewItemIndex(items, archivoId);
  const showNav = items.length > 1;
  const counter =
    showNav && index >= 0 ? `${index + 1} de ${items.length}` : null;
  return {
    showNav,
    counter,
    index,
    canGoPrevious: showNav && index > 0,
    canGoNext: showNav && index >= 0 && index < items.length - 1,
  };
}

export function adjacentPreviewArchivoId(
  items: MediaArchivoListItem[],
  currentArchivoId: number,
  direction: "previous" | "next"
): number | null {
  const index = findPreviewItemIndex(items, currentArchivoId);
  if (index < 0) return null;
  const nextIndex = direction === "previous" ? index - 1 : index + 1;
  if (nextIndex < 0 || nextIndex >= items.length) return null;
  return items[nextIndex]?.archivo_id ?? null;
}

/** Cierra el visor si el archivo activo ya no está en la lista READY de la categoría. */
export function shouldCloseMediaPreview(
  items: MediaArchivoListItem[],
  activeArchivoId: number | null
): boolean {
  if (activeArchivoId == null) return false;
  if (items.length === 0) return true;
  return !items.some((i) => i.archivo_id === activeArchivoId);
}

export function buildMediaPreviewDialogTitle(
  categoryLabel: string,
  nav: MediaPreviewNavState,
  fallbackFilename: string | undefined
): string {
  return nav.counter != null
    ? `${categoryLabel} · ${nav.counter}`
    : fallbackFilename ?? "Archivo";
}

/** Cambio de ítem activo: el visor debe reiniciar zoom y pan (misma clave de efecto que archivo_id). */
export function shouldResetPreviewViewOnArchivoChange(
  previousArchivoId: number | null,
  nextArchivoId: number | null
): boolean {
  return previousArchivoId != null && nextArchivoId != null && previousArchivoId !== nextArchivoId;
}
