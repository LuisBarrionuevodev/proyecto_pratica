import { describe, expect, it } from "vitest";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";
import type { MediaQueuedFile } from "../mediaTypes";
import { mergeMediaQueueItemPatch } from "./mediaQueueItemPatch";

function base(overrides: Partial<MediaQueuedFile> = {}): MediaQueuedFile {
  return {
    localId: "a",
    file: new File(["x"], "a.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase: "ready",
    progressPct: 100,
    errorMessage: null,
    archivoId: 9,
    previewUrl: "blob:x",
    ...overrides,
  };
}

describe("mergeMediaQueueItemPatch (MEDIA.2E.1B)", () => {
  it("no degrada READY a error por callback tardío", () => {
    const item = base();
    const next = mergeMediaQueueItemPatch(item, {
      phase: "error",
      errorMessage: "Network Error",
      progressPct: 0,
    });
    expect(next.phase).toBe("ready");
    expect(next.errorMessage).toBeNull();
    expect(next.archivoId).toBe(9);
  });

  it("permite enriquecer READY sin tocar fase", () => {
    const item = base({ archivoId: 1 });
    const next = mergeMediaQueueItemPatch(item, { archivoId: 1, previewUrl: "blob:y" });
    expect(next.phase).toBe("ready");
    expect(next.previewUrl).toBe("blob:y");
  });
});
