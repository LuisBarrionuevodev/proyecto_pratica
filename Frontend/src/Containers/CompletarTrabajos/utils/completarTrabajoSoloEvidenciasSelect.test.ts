import { describe, expect, it, beforeEach, vi } from "vitest";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import {
  __resetRutaItemMediaUploadStoreForTests,
  addFilesForRutaItem,
  getRutaItemMediaUploadSnapshot,
  uploadAllForRutaItem,
} from "../../../features/media/rutaItemMediaUploadStore";

vi.mock("../../../features/media/mediaUploadPipeline", () => ({
  uploadQueuedFilesWithConcurrency: vi.fn(async () => undefined),
}));

/**
 * Simula reapertura de trabajo con fotos READY en servidor + selección local (sin jsdom).
 */
describe("completarTrabajo solo fotos pendientes — selección", () => {
  beforeEach(() => {
    __resetRutaItemMediaUploadStoreForTests();
  });

  it("inicializa cola del rutaItemId activo y agrega pendientes tras selección", () => {
    const rutaItemId = 42;
    const before = getRutaItemMediaUploadSnapshot(rutaItemId);
    expect(before.items).toHaveLength(0);

    const file = new File(["x"], "galeria.jpg", { type: "image/jpeg" });
    const result = addFilesForRutaItem(rutaItemId, MEDIA_CATEGORIA_FOTO_ACTA, [file], 3);

    expect(result.added).toBe(1);
    const after = getRutaItemMediaUploadSnapshot(rutaItemId);
    expect(after.items).toHaveLength(1);
    expect(after.items[0]?.file.name).toBe("galeria.jpg");
    expect(after.items[0]?.phase).toBe("pending");
    expect(after.uploadableCount).toBe(1);
    expect(getRutaItemMediaUploadSnapshot(99).items).toHaveLength(0);
  });

  it("dos lecturas tras selección comparten la misma referencia de snapshot", () => {
    const rutaItemId = 42;
    addFilesForRutaItem(rutaItemId, MEDIA_CATEGORIA_FOTO_ACTA, [
      new File(["x"], "galeria.jpg", { type: "image/jpeg" }),
    ], 0);
    const a = getRutaItemMediaUploadSnapshot(rutaItemId);
    const b = getRutaItemMediaUploadSnapshot(rutaItemId);
    expect(a).toBe(b);
    expect(a.items).toHaveLength(1);
  });

  it("cola vacía: uploadAll no deja ítems en error ni muta READY del store", async () => {
    const rutaItemId = 55;
    const snap = getRutaItemMediaUploadSnapshot(rutaItemId);
    expect(snap.uploadableCount).toBe(0);
    await uploadAllForRutaItem(rutaItemId, 1);
    expect(getRutaItemMediaUploadSnapshot(rutaItemId).items).toHaveLength(0);
  });
});
