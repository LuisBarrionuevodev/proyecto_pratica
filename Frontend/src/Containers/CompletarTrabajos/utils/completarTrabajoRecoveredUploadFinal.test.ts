import { describe, expect, it, vi } from "vitest";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import {
  applyCompletarTrabajoRecoveredUploadSuccess,
  confirmCompletarTrabajoEvidenciasDefinitiveSuccess,
  patchRowSinEvidenciasPendientes,
  runCompletarTrabajoSoloEvidenciasFlow,
} from "./completarTrabajoRecoveredUploadFinal";

function queued(phase: MediaQueuedFile["phase"], archivoId: number | null = null): MediaQueuedFile {
  return {
    localId: "a",
    file: new File(["x"], "f.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase,
    progressPct: phase === "ready" ? 100 : 0,
    errorMessage: null,
    archivoId,
    previewUrl: null,
  };
}

describe("completarTrabajoRecoveredUploadFinal", () => {
  it("applyCompletarTrabajoRecoveredUploadSuccess ejecuta cierre en orden", () => {
    const order: string[] = [];
    applyCompletarTrabajoRecoveredUploadSuccess(5, {
      clearTransientErrors: () => order.push("errors"),
      clearUploadState: () => order.push("upload"),
      invalidateEvidenciasPendientesLocal: () => order.push("invalidate"),
      notifyPendientesRefresh: () => order.push("refresh"),
      showSuccessToast: () => order.push("toast"),
      removeFromList: () => order.push("list"),
      closeModal: () => order.push("close"),
    });
    expect(order).toEqual(["errors", "upload", "invalidate", "refresh", "toast", "list", "close"]);
  });

  it("cola 3/3 READY sin uploadable → confirm success", async () => {
    const items = [queued("ready", 1), queued("ready", 2), queued("ready", 3)];
    const clear = vi.fn();
    const result = await confirmCompletarTrabajoEvidenciasDefinitiveSuccess({
      rutaItemId: 1,
      uploadAll: vi.fn(),
      getQueueItems: () => items,
      applyQueueItems: vi.fn(),
      clearUploadedFromQueue: clear,
      reloadServer: vi.fn(),
      fetchDetalleForConfirm: vi.fn().mockResolvedValue({
        ui_policy: { solo_evidencias_pendientes: true, cierre_alfanumerico_readonly: true },
        row: {
          trabajo_guardado_evidencias_pendientes: true,
          media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
        },
      }),
    });
    expect(result.outcome).toBe("success");
    expect(clear).toHaveBeenCalled();
  });

  it("runCompletarTrabajoSoloEvidenciasFlow sin uploadable delega a confirm", async () => {
    const items = [queued("ready", 1)];
    const result = await runCompletarTrabajoSoloEvidenciasFlow({
      rutaItemId: 2,
      uploadAll: vi.fn(),
      getQueueItems: () => items,
      applyQueueItems: vi.fn(),
      clearUploadedFromQueue: vi.fn(),
      reloadServer: vi.fn(),
      fetchDetalleForConfirm: vi.fn().mockResolvedValue({
        ui_policy: { solo_evidencias_pendientes: true, cierre_alfanumerico_readonly: true },
        row: {
          media_resumen: { evidencias_pendientes_total: 0, tiene_evidencias_pendientes: false },
        },
      }),
    });
    expect(result.outcome).toBe("success");
  });

  it("patchRowSinEvidenciasPendientes limpia flags locales", () => {
    const row = patchRowSinEvidenciasPendientes({
      trabajo_guardado_evidencias_pendientes: true,
      media_resumen: { tiene_evidencias_pendientes: true, evidencias_pendientes_total: 3 },
    });
    expect(row.trabajo_guardado_evidencias_pendientes).toBe(false);
    expect(row.media_resumen?.evidencias_pendientes_total).toBe(0);
  });
});
