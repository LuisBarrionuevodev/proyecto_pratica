import { describe, expect, it } from "vitest";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import { reconcileQueueItemsWithServerArchivos } from "../../../features/media/utils/mediaUploadQueueReconcile";

function queued(
  phase: MediaQueuedFile["phase"],
  archivoId: number | null = null
): MediaQueuedFile {
  return {
    localId: "a",
    file: new File(["x"], "f.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase,
    progressPct: 0,
    errorMessage: phase === "error" ? "Red" : null,
    archivoId,
    previewUrl: null,
  };
}

describe("reconcileQueueItemsWithServerArchivos", () => {
  it("marca READY local si el archivoId está en el listado", () => {
    const items = [queued("error", 42)];
    const server = {
      foto_acta: [
        {
          archivo_id: 42,
          original_filename: "f.jpg",
          content_type: "image/jpeg",
          byte_size: 1,
          uploaded_at: "2026-01-01",
          categoria: MEDIA_CATEGORIA_FOTO_ACTA,
        },
      ],
      foto_documentacion_local: [],
      foto_inspeccion: [],
    };
    const next = reconcileQueueItemsWithServerArchivos(items, server);
    expect(next[0].phase).toBe("ready");
  });
});
