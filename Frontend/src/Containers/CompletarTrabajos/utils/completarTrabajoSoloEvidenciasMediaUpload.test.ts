import { describe, expect, it, vi } from "vitest";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import {
  runCompletarTrabajoSoloEvidenciasMediaUpload,
  shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload,
} from "./completarTrabajoSoloEvidenciasMediaUpload";

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

describe("completarTrabajoSoloEvidenciasMediaUpload", () => {
  it("corte + reconexión + READY en servidor → success y debe cerrar", async () => {
    let items: MediaQueuedFile[] = [queued("error", null)];
    const uploadAll = vi.fn(async () => {
      items = [queued("error", 7)];
    });
    const apply = vi.fn((next: MediaQueuedFile[]) => {
      items = next;
    });
    const clear = vi.fn(() => {
      items = items.filter((x) => x.phase !== "ready");
    });
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 1,
      uploadAll,
      getQueueItems: () => items,
      applyQueueItems: apply,
      clearUploadedFromQueue: clear,
      reloadServer: vi.fn(),
      fetchArchivosForReconcile: vi.fn().mockResolvedValue({
        foto_acta: [
          {
            archivo_id: 7,
            original_filename: "f.jpg",
            content_type: "image/jpeg",
            byte_size: 1,
            uploaded_at: "2026-01-01",
            categoria: MEDIA_CATEGORIA_FOTO_ACTA,
          },
        ],
        foto_documentacion_local: [],
        foto_inspeccion: [],
      }),
    });

    expect(uploadAll).toHaveBeenCalled();
    expect(result.outcome).toBe("success");
    expect(shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(result.outcome)).toBe(true);
    expect(clear).toHaveBeenCalled();
  });

  it("queda pendiente real → partial y no cierra", async () => {
    let items: MediaQueuedFile[] = [queued("pending", null)];
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 2,
      uploadAll: vi.fn(),
      getQueueItems: () => items,
      applyQueueItems: (next) => {
        items = next;
      },
      clearUploadedFromQueue: vi.fn(),
      reloadServer: vi.fn(),
      fetchArchivosForReconcile: vi.fn().mockResolvedValue({
        foto_acta: [],
        foto_documentacion_local: [],
        foto_inspeccion: [],
      }),
    });
    expect(result.outcome).toBe("partial");
    expect(shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(result.outcome)).toBe(false);
  });

  it("refresh visual fallido con archivos READY → success", async () => {
    let items: MediaQueuedFile[] = [queued("pending", null)];
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 3,
      uploadAll: vi.fn(async () => {
        items = [queued("ready", 1)];
      }),
      getQueueItems: () => items,
      applyQueueItems: (next) => {
        items = next;
      },
      clearUploadedFromQueue: () => {
        items = [];
      },
      reloadServer: vi.fn().mockRejectedValue(new Error("refresh")),
    });
    expect(result.outcome).toBe("success");
    expect(result.refreshFailed).toBe(true);
  });
});
