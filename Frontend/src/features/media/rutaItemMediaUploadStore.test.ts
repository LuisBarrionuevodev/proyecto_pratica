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
