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
    progressPct: phase === "ready" ? 100 : 0,
    errorMessage: phase === "error" ? "Red" : null,
    archivoId,
    previewUrl: null,
  };
}

const detalleCompleto = {
  ui_policy: { solo_evidencias_pendientes: true, cierre_alfanumerico_readonly: true },
  row: {
    trabajo_guardado_evidencias_pendientes: false,
    media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
  },
};

const detallePendiente = {
  ui_policy: { solo_evidencias_pendientes: true },
  row: {
    media_resumen: { tiene_evidencias_pendientes: true, evidencias_pendientes_total: 1 },
  },
};

describe("completarTrabajoSoloEvidenciasMediaUpload", () => {
  it("corte → READY local + backend completo → success y cierra", async () => {
    let items: MediaQueuedFile[] = [queued("error", null)];
    const uploadAll = vi.fn(async () => {
      items = [queued("error", 7)];
    });
    const clear = vi.fn(() => {
      items = items.filter((x) => x.phase !== "ready");
    });
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 1,
      uploadAll,
      getQueueItems: () => items,
      applyQueueItems: (next) => {
        items = next;
      },
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
      fetchDetalleForConfirm: vi.fn().mockResolvedValue(detalleCompleto),
    });

    expect(result.outcome).toBe("success");
    expect(shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(result.outcome)).toBe(true);
    expect(clear).toHaveBeenCalled();
  });

  it("local partial pero backend confirma sin pendientes → success definitivo", async () => {
    let items: MediaQueuedFile[] = [queued("ready", 1), queued("ready", 2)];
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 2,
      uploadAll: vi.fn(),
      getQueueItems: () => items,
      applyQueueItems: (next) => {
        items = next;
      },
      clearUploadedFromQueue: vi.fn(() => {
        items = [];
      }),
      reloadServer: vi.fn(),
      fetchDetalleForConfirm: vi.fn().mockResolvedValue(detalleCompleto),
    });
    expect(result.outcome).toBe("success");
  });

  it("backend con pendientes → partial y no cierra", async () => {
    let items: MediaQueuedFile[] = [queued("pending", null)];
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 3,
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
      fetchDetalleForConfirm: vi.fn().mockResolvedValue(detallePendiente),
    });
    expect(result.outcome).toBe("partial");
    expect(shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(result.outcome)).toBe(false);
  });

  it("éxito confirmado + refresh visual fallido → success sin degradar", async () => {
    let items: MediaQueuedFile[] = [queued("pending", null)];
    const result = await runCompletarTrabajoSoloEvidenciasMediaUpload({
      rutaItemId: 4,
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
      fetchDetalleForConfirm: vi.fn().mockResolvedValue(detalleCompleto),
    });
    expect(result.outcome).toBe("success");
    expect(result.refreshFailed).toBe(true);
  });
});
