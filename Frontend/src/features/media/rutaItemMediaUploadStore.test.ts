import { describe, expect, it, vi, beforeEach } from "vitest";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "./mediaConstants";
import type { MediaQueuedFile } from "./mediaTypes";
import {
  __resetRutaItemMediaUploadStoreForTests,
  addFilesForRutaItem,
  cancelUploadForRutaItem,
  getRutaItemMediaUploadSnapshot,
  MEDIA_UPLOAD_INTERRUPTED_MESSAGE,
  replaceQueueItemsForRutaItem,
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

  it("error con archivoId no habilita continuar subida (uploadableCount 0)", () => {
    addFilesForRutaItem(30, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("z.jpg")], 0);
    const base = getRutaItemMediaUploadSnapshot(30).items[0]!;
    replaceQueueItemsForRutaItem(30, [
      { ...base, phase: "error", archivoId: 9, errorMessage: "Red" },
    ]);
    const snap = getRutaItemMediaUploadSnapshot(30);
    expect(snap.uploadableCount).toBe(0);
    expect(snap.hasRetryableUpload).toBe(false);
  });

  it("cancelar ítem en uploading vuelve a pending y conserva file/localId/preview", () => {
    addFilesForRutaItem(40, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("up.jpg")], 0);
    const base = getRutaItemMediaUploadSnapshot(40).items[0]!;
    const previewUrl = "blob:preview-test";
    replaceQueueItemsForRutaItem(40, [
      { ...base, phase: "uploading", progressPct: 42, previewUrl },
    ]);
    cancelUploadForRutaItem(40);
    const item = getRutaItemMediaUploadSnapshot(40).items[0]!;
    expect(item.phase).toBe("pending");
    expect(item.progressPct).toBe(0);
    expect(item.file).toBe(base.file);
    expect(item.localId).toBe(base.localId);
    expect(item.previewUrl).toBe(previewUrl);
    expect(item.errorMessage).toBe(MEDIA_UPLOAD_INTERRUPTED_MESSAGE);
    expect(getRutaItemMediaUploadSnapshot(40).session.active).toBe(false);
  });

  it("cancelar recupera preparing y verifying a pending", () => {
    addFilesForRutaItem(41, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("a.jpg"), fakeFile("b.jpg")], 0);
    const [a, b] = getRutaItemMediaUploadSnapshot(41).items;
    replaceQueueItemsForRutaItem(41, [
      { ...a!, phase: "preparing", progressPct: 10 },
      { ...b!, phase: "verifying", progressPct: 90 },
    ]);
    cancelUploadForRutaItem(41);
    const snap = getRutaItemMediaUploadSnapshot(41);
    expect(snap.items[0]?.phase).toBe("pending");
    expect(snap.items[1]?.phase).toBe("pending");
    expect(snap.items[0]?.progressPct).toBe(0);
    expect(snap.items[1]?.progressPct).toBe(0);
  });

  it("cancelar no modifica ítems READY", () => {
    addFilesForRutaItem(42, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("done.jpg")], 0);
    const base = getRutaItemMediaUploadSnapshot(42).items[0]!;
    replaceQueueItemsForRutaItem(42, [
      { ...base, phase: "ready", progressPct: 100, archivoId: 77 },
    ]);
    cancelUploadForRutaItem(42);
    const item = getRutaItemMediaUploadSnapshot(42).items[0]!;
    expect(item.phase).toBe("ready");
    expect(item.archivoId).toBe(77);
    expect(getRutaItemMediaUploadSnapshot(42).items).toHaveLength(1);
  });

  it("tras cancelar, uploadAll reintenta el ítem recuperado hasta READY", async () => {
    const rutaItemId = 1;
    addFilesForRutaItem(rutaItemId, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("retry.jpg")], 0);
    const base = getRutaItemMediaUploadSnapshot(rutaItemId).items[0]!;
    replaceQueueItemsForRutaItem(rutaItemId, [{ ...base, phase: "uploading", progressPct: 33 }]);
    cancelUploadForRutaItem(rutaItemId);
    expect(getRutaItemMediaUploadSnapshot(rutaItemId).items[0]?.phase).toBe("pending");
    expect(getRutaItemMediaUploadSnapshot(rutaItemId).hasRetryableUpload).toBe(true);
    await uploadAllForRutaItem(rutaItemId, 1);
    expect(getRutaItemMediaUploadSnapshot(rutaItemId).items[0]?.phase).toBe("ready");
  });

  it("cambiar de trabajo: cancel solo afecta la cola del rutaItem cancelado", () => {
    addFilesForRutaItem(50, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("a.jpg")], 0);
    addFilesForRutaItem(51, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("b.jpg")], 0);
    const item50 = getRutaItemMediaUploadSnapshot(50).items[0]!;
    const item51 = getRutaItemMediaUploadSnapshot(51).items[0]!;
    replaceQueueItemsForRutaItem(50, [{ ...item50, phase: "uploading", progressPct: 20 }]);
    replaceQueueItemsForRutaItem(51, [{ ...item51, phase: "pending", progressPct: 0 }]);
    cancelUploadForRutaItem(50);
    expect(getRutaItemMediaUploadSnapshot(50).items[0]?.phase).toBe("pending");
    expect(getRutaItemMediaUploadSnapshot(51).items[0]?.phase).toBe("pending");
    expect(getRutaItemMediaUploadSnapshot(51).items[0]?.errorMessage).toBeNull();
    expect(getRutaItemMediaUploadSnapshot(50).items[0]?.errorMessage).toBe(
      MEDIA_UPLOAD_INTERRUPTED_MESSAGE
    );
  });

  it("respuestas tardías no actualizan otro rutaItemId tras cancel", async () => {
    addFilesForRutaItem(1, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("one.jpg")], 0);
    addFilesForRutaItem(2, MEDIA_CATEGORIA_FOTO_ACTA, [fakeFile("two.jpg")], 0);
    const uploadPromise = uploadAllForRutaItem(2, 1);
    cancelUploadForRutaItem(2);
    await uploadAllForRutaItem(1, 1);
    await uploadPromise.catch(() => undefined);
    const snap2 = getRutaItemMediaUploadSnapshot(2);
    expect(snap2.items[0]?.phase).toBe("pending");
    expect(snap2.items[0]?.errorMessage).toBe(MEDIA_UPLOAD_INTERRUPTED_MESSAGE);
    expect(getRutaItemMediaUploadSnapshot(1).items[0]?.phase).toBe("ready");
  });
});
