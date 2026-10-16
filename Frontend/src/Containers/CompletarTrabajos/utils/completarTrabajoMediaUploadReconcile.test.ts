import { describe, expect, it, vi } from "vitest";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import {
  finalizeCompletarTrabajoMediaUploadAttempt,
  reconcileQueueItemsWithServerArchivos,
} from "./completarTrabajoMediaUploadReconcile";

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

describe("finalizeCompletarTrabajoMediaUploadAttempt", () => {
  it("éxito si la cola local ya no tiene pendientes", async () => {
    const result = await finalizeCompletarTrabajoMediaUploadAttempt({
      rutaItemId: 1,
      queueItems: [queued("ready", 1)],
      fetchArchivos: vi.fn(),
      fetchDetalle: vi.fn(),
    });
    expect(result.status).toBe("success");
    expect(result.archivosRefreshFailed).toBe(false);
  });

  it("error de red local + archivo READY en servidor → success", async () => {
    const result = await finalizeCompletarTrabajoMediaUploadAttempt({
      rutaItemId: 2,
      queueItems: [queued("error", 99)],
      fetchArchivos: vi.fn().mockResolvedValue({
        foto_acta: [
          {
            archivo_id: 99,
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
      fetchDetalle: vi.fn(),
    });
    expect(result.status).toBe("success");
    expect(result.reconciledItems[0].phase).toBe("ready");
  });

  it("refresh de archivos fallido pero detalle completo → success", async () => {
    const result = await finalizeCompletarTrabajoMediaUploadAttempt({
      rutaItemId: 3,
      queueItems: [queued("error", null)],
      fetchArchivos: vi.fn().mockRejectedValue(new Error("network")),
      fetchDetalle: vi.fn().mockResolvedValue({
        ui_policy: { solo_evidencias_pendientes: true, cierre_alfanumerico_readonly: true },
        row: {
          trabajo_guardado_evidencias_pendientes: false,
          media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
        },
      }),
    });
    expect(result.status).toBe("success");
    expect(result.archivosRefreshFailed).toBe(true);
  });

  it("archivo realmente pendiente → partial", async () => {
    const result = await finalizeCompletarTrabajoMediaUploadAttempt({
      rutaItemId: 4,
      queueItems: [queued("pending", null)],
      fetchArchivos: vi.fn().mockResolvedValue({
        foto_acta: [],
        foto_documentacion_local: [],
        foto_inspeccion: [],
      }),
      fetchDetalle: vi.fn().mockResolvedValue({
        ui_policy: { solo_evidencias_pendientes: true },
        row: {
          media_resumen: { tiene_evidencias_pendientes: true, evidencias_pendientes_total: 1 },
        },
      }),
    });
    expect(result.status).toBe("guardado_fotos_pendientes");
  });
});
