import { describe, expect, it, vi } from "vitest";
import * as mediaApi from "../../api/mediaApi";
import { MEDIA_CATEGORIA_FOTO_INSPECCION } from "./mediaConstants";
import { MOBILE_UPLOAD_CONCURRENCY } from "./mediaUploadPipeline";
import { MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE } from "./utils/mediaUploadMessages";
import type { MediaQueuedFile } from "./mediaTypes";

describe("mediaUploadPipeline", () => {
  it("usa concurrencia 1 para móvil por defecto", () => {
    expect(MOBILE_UPLOAD_CONCURRENCY).toBe(1);
  });

  it("archivo ilegible: no llama a postMediaUploadIntent y traduce el error", async () => {
    const intentSpy = vi.spyOn(mediaApi, "postMediaUploadIntent");
    const file = new File(["x"], "foto.jpg", { type: "image/jpeg" });
    file.arrayBuffer = () =>
      Promise.reject(
        new DOMException(
          "The requested file could not be read, typically due to permission problems that have occurred after a reference to a file was acquired from.",
          "NotReadableError"
        )
      );
    const { uploadSingleQueuedFile } = await import("./mediaUploadPipeline");
    const item: MediaQueuedFile = {
      localId: "illegible-1",
      file,
      categoria: MEDIA_CATEGORIA_FOTO_INSPECCION,
      tipoDocumento: null,
      phase: "pending",
      progressPct: 0,
      errorMessage: null,
      archivoId: null,
      previewUrl: null,
    };
    await expect(uploadSingleQueuedFile(1, item)).rejects.toThrow(MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE);
    expect(intentSpy).not.toHaveBeenCalled();
    intentSpy.mockRestore();
  });
});
