import { describe, expect, it, vi, beforeEach } from "vitest";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "./mediaConstants";
import type { MediaQueuedFile } from "./mediaTypes";
import {
  __resetRutaItemMediaUploadStoreForTests,
  addFilesForRutaItem,
  cancelUploadForRutaItem,
  getRutaItemMediaUploadSnapshot,
  uploadAllForRutaItem,
} from "./rutaItemMediaUploadStore";

vi.mock("./mediaUploadPipeline", () => ({
  uploadQueuedFilesWithConcurrency: vi.fn(
    async (
      rutaItemId: number,
      items: MediaQueuedFile[],
      options: {
        onItemPhase?: (
          localId: string,
          phase: MediaQueuedFile["phase"],
          progressPct?: number
        ) => void;
        isStale?: () => boolean;
      }
    ) => {
      if (options.isStale?.()) return;
      const target = items.find((x) => x.phase === "pending" || x.phase === "error");
      if (!target) return;
      if (rutaItemId === 1) {
        options.onItemPhase?.(target.localId, "ready", 100);
      }
      if (rutaItemId === 2) {
        options.onItemPhase?.(target.localId, "uploading", 50);
        await new Promise((r) => setTimeout(r, 50));
        if (options.isStale?.()) return;
        options.onItemPhase?.(target.localId, "ready", 100);
      }
    }
  ),
}));

function fakeFile(name: string): File {
  return new File(["x"], name, { type: "image/jpeg" });
}

describe("rutaItemMediaUploadStore", () => {
  beforeEach(() => {
    __resetRutaItemMediaUploadStoreForTests();
  });

  it("aisla colas por rutaItemId", () => {
    addFilesForRutaItem(10, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("a.jpg")], 0);
    addFilesForRutaItem(20, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("b.jpg")], 0);
    expect(getRutaItemMediaUploadSnapshot(10).items).toHaveLength(1);
    expect(getRutaItemMediaUploadSnapshot(10).items[0]?.file.name).toBe("a.jpg");
    expect(getRutaItemMediaUploadSnapshot(20).items[0]?.file.name).toBe("b.jpg");
    expect(getRutaItemMediaUploadSnapshot(99).items).toHaveLength(0);
  });

  it("acepta archivos sin MIME (galería móvil) sin lanzar error", () => {
    const mobileLike = new File(["x"], "cam.jpg", { type: "" });
    expect(() =>
      addFilesForRutaItem(7, MEDIA_CATEGORIA_FOTO_ACTA, [mobileLike], 0)
    ).not.toThrow();
    expect(getRutaItemMediaUploadSnapshot(7).items).toHaveLength(0);
  });

  it("getRutaItemMediaUploadSnapshot mantiene referencia estable sin mutación (useSyncExternalStore)", () => {
    addFilesForRutaItem(10, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("a.jpg")], 0);
    const first = getRutaItemMediaUploadSnapshot(10);
    const second = getRutaItemMediaUploadSnapshot(10);
    expect(first).toBe(second);
    expect(first.items).toHaveLength(1);
  });

  it("agregar archivos no duplica la cola en lecturas consecutivas", () => {
    const rutaItemId = 11;
    const files = [fakeFile("one.jpg"), fakeFile("two.jpg")];
    addFilesForRutaItem(rutaItemId, MEDIA_CATEGORIA_FOTO_ACTA, files, 0);
    const snap = getRutaItemMediaUploadSnapshot(rutaItemId);
    expect(snap.items).toHaveLength(2);
    expect(getRutaItemMediaUploadSnapshot(rutaItemId).items).toBe(snap.items);
  });

  it("addFiles sin ítems aceptados no invalida snapshot ni emite cambio vacío", () => {
    addFilesForRutaItem(12, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("x.jpg")], 0);
    const before = getRutaItemMediaUploadSnapshot(12);
    const mobileLike = new File(["x"], "cam.jpg", { type: "" });
    addFilesForRutaItem(12, MEDIA_CATEGORIA_FOTO_ACTA, [mobileLike], 0);
    const after = getRutaItemMediaUploadSnapshot(12);
    expect(after).toBe(before);
    expect(after.items).toHaveLength(1);
  });

  it("respuestas tardías no actualizan otro rutaItemId tras cancel", async () => {
    addFilesForRutaItem(1, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("one.jpg")], 0);
    addFilesForRutaItem(2, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("two.jpg")], 0);
    const uploadPromise = uploadAllForRutaItem(2, 1);
    cancelUploadForRutaItem(2);
    await uploadAllForRutaItem(1, 1);
    await uploadPromise.catch(() => undefined);
    const snap2 = getRutaItemMediaUploadSnapshot(2);
    expect(snap2.items[0]?.phase).not.toBe("ready");
    expect(getRutaItemMediaUploadSnapshot(1).items[0]?.phase).toBe("ready");
  });
});
