import { describe, expect, it, beforeEach } from "vitest";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import {
  __resetRutaItemMediaUploadStoreForTests,
  addFilesForRutaItem,
  getRutaItemMediaUploadSnapshot,
} from "../../../features/media/rutaItemMediaUploadStore";

/**
 * Simula reapertura de trabajo con fotos READY en servidor + selección local (sin jsdom).
 */
describe("completarTrabajo solo fotos pendientes — selección", () => {
  beforeEach(() => {
    __resetRutaItemMediaUploadStoreForTests();
  });

  it("inicializa cola del rutaItemId activo y agrega pendientes tras FileList", () => {
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
    expect(getRutaItemMediaUploadSnapshot(99).items).toHaveLength(0);
  });
});
