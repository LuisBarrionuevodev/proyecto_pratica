import { describe, expect, it, vi } from "vitest";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";
import type { MediaQueuedFile } from "../mediaTypes";
import {
  queueNeedsServerReconciliation,
  reconcileMediaQueueAfterUploadAttempt,
  reconcileQueueItemsWithServerArchivos,
} from "./mediaUploadQueueReconcile";

function item(overrides: Partial<MediaQueuedFile>): MediaQueuedFile {
  return {
    localId: "x",
    file: new File(["a"], "a.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase: "pending",
    progressPct: 0,
    errorMessage: null,
    archivoId: null,
    previewUrl: null,
    ...overrides,
  };
}

describe("mediaUploadQueueReconcile (MEDIA.2E.1B)", () => {
  it("marca READY solo si el listado remoto incluye archivoId", () => {
    const rows = reconcileQueueItemsWithServerArchivos(
      [item({ phase: "error", archivoId: 5, errorMessage: "Red" })],
      {
        foto_acta: [
          {
            archivo_id: 5,
            original_filename: "a.jpg",
            content_type: "image/jpeg",
            byte_size: 1,
            uploaded_at: "2026-01-01",
            categoria: MEDIA_CATEGORIA_FOTO_ACTA,
          },
        ],
        foto_documentacion_local: [],
        foto_inspeccion: [],
      }
    );
    expect(rows[0]?.phase).toBe("ready");
    expect(rows[0]?.errorMessage).toBeNull();
  });

  it("reconcilia tras error con archivoId del intent", async () => {
    const fetch = vi.fn().mockResolvedValue({
      foto_acta: [
        {
          archivo_id: 77,
          original_filename: "a.jpg",
          content_type: "image/jpeg",
          byte_size: 1,
          uploaded_at: "2026-01-01",
          categoria: MEDIA_CATEGORIA_FOTO_ACTA,
        },
      ],
      foto_documentacion_local: [],
      foto_inspeccion: [],
    });
    const { items } = await reconcileMediaQueueAfterUploadAttempt(
      3,
      [item({ phase: "error", archivoId: 77, errorMessage: "Network Error" })],
      fetch
    );
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(items[0]?.phase).toBe("ready");
  });

  it("no reconcilia si isCancelled", async () => {
    const fetch = vi.fn();
    const { items } = await reconcileMediaQueueAfterUploadAttempt(
      1,
      [item({ phase: "error", archivoId: 1 })],
      fetch,
      { isCancelled: () => true }
    );
    expect(fetch).not.toHaveBeenCalled();
    expect(items[0]?.phase).toBe("error");
  });

  it("queueNeedsServerReconciliation detecta error con archivoId", () => {
    expect(queueNeedsServerReconciliation([item({ phase: "error", archivoId: 2 })])).toBe(true);
    expect(queueNeedsServerReconciliation([item({ phase: "error", archivoId: null })])).toBe(false);
  });
});
