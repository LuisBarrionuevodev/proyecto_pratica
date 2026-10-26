import { describe, expect, it } from "vitest";
import type { MediaArchivoListItem } from "../mediaTypes";
import { MEDIA_CATEGORIA_FOTO_INSPECCION } from "../mediaConstants";
import {
  adjacentPreviewArchivoId,
  buildMediaPreviewDialogTitle,
  getMediaPreviewNavState,
  shouldCloseMediaPreview,
  shouldResetPreviewViewOnArchivoChange,
} from "./mediaPreviewNavigation";
import { MEDIA_CATEGORY_LABELS } from "../mediaConstants";

function item(id: number): MediaArchivoListItem {
  return {
    archivo_id: id,
    original_filename: `foto-${id}.jpg`,
    content_type: "image/jpeg",
    byte_size: 1024,
    uploaded_at: "2026-01-01T00:00:00Z",
    categoria: MEDIA_CATEGORIA_FOTO_INSPECCION,
  };
}

describe("mediaPreviewNavigation V1.1-MEDIA-UX.1", () => {
  const eight = Array.from({ length: 8 }, (_, i) => item(i + 1));

  it("tercer ítem de ocho: contador 3 de 8", () => {
    const nav = getMediaPreviewNavState(eight, 3);
    expect(nav.counter).toBe("3 de 8");
    expect(nav.index).toBe(2);
    expect(nav.showNav).toBe(true);
    expect(nav.canGoPrevious).toBe(true);
    expect(nav.canGoNext).toBe(true);
  });

  it("límites anterior y siguiente", () => {
    const first = getMediaPreviewNavState(eight, 1);
    expect(first.canGoPrevious).toBe(false);
    expect(first.canGoNext).toBe(true);

    const last = getMediaPreviewNavState(eight, 8);
    expect(last.canGoPrevious).toBe(true);
    expect(last.canGoNext).toBe(false);
  });

  it("un solo ítem: sin navegación ni contador", () => {
    const nav = getMediaPreviewNavState([item(1)], 1);
    expect(nav.showNav).toBe(false);
    expect(nav.counter).toBeNull();
  });

  it("adjacentPreviewArchivoId recorre la categoría", () => {
    expect(adjacentPreviewArchivoId(eight, 3, "previous")).toBe(2);
    expect(adjacentPreviewArchivoId(eight, 3, "next")).toBe(4);
    expect(adjacentPreviewArchivoId(eight, 1, "previous")).toBeNull();
    expect(adjacentPreviewArchivoId(eight, 8, "next")).toBeNull();
  });

  it("shouldCloseMediaPreview si el activo ya no está en la lista", () => {
    expect(shouldCloseMediaPreview(eight, 5)).toBe(false);
    expect(shouldCloseMediaPreview(eight.filter((x) => x.archivo_id !== 5), 5)).toBe(true);
    expect(shouldCloseMediaPreview([], 1)).toBe(true);
  });

  it("título con categoría y contador", () => {
    const nav = getMediaPreviewNavState(eight, 3);
    expect(
      buildMediaPreviewDialogTitle(
        MEDIA_CATEGORY_LABELS[MEDIA_CATEGORIA_FOTO_INSPECCION],
        nav,
        "evidencia-3.jpg"
      )
    ).toBe("Fotos de la inspección · 3 de 8");
  });

  it("cambio de archivo activo reinicia zoom/pan", () => {
    expect(shouldResetPreviewViewOnArchivoChange(2, 3)).toBe(true);
    expect(shouldResetPreviewViewOnArchivoChange(3, 3)).toBe(false);
  });
});
