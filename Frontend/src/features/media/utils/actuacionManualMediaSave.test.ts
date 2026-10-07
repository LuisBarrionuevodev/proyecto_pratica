import { describe, expect, it, vi } from "vitest";
import type { MediaQueuedFile } from "../mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";
import { countUploadableQueueItems, runManualMediaSave } from "./actuacionManualMediaSave";

function pendingItem(id: string): MediaQueuedFile {
  return {
    localId: id,
    file: new File(["x"], "a.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase: "pending",
    progressPct: 0,
    errorMessage: null,
    archivoId: null,
    previewUrl: null,
  };
}

describe("actuacionManualMediaSave", () => {
  it("cola vacía no llama uploadAll", async () => {
    const uploadAll = vi.fn();
    const result = await runManualMediaSave({
      rutaItemId: 1,
      uploadAll,
      getQueueItems: () => [],
      clearUploadedFromQueue: vi.fn(),
      reloadServer: vi.fn(),
    });
    expect(result.outcome).toBe("empty");
    expect(uploadAll).not.toHaveBeenCalled();
  });

  it("éxito completo limpia cola y refresca", async () => {
    let items: MediaQueuedFile[] = [pendingItem("a")];
    const uploadAll = vi.fn(async () => {
      items = items.map((x) => ({ ...x, phase: "ready" as const, archivoId: 9 }));
    });
    const clear = vi.fn(() => {
      items = items.filter((x) => x.phase !== "ready");
    });
    const reload = vi.fn();
    const result = await runManualMediaSave({
      rutaItemId: 2,
      uploadAll,
      getQueueItems: () => items,
      clearUploadedFromQueue: clear,
      reloadServer: reload,
    });
    expect(uploadAll).toHaveBeenCalledTimes(1);
    expect(clear).toHaveBeenCalled();
    expect(reload).toHaveBeenCalled();
    expect(result.outcome).toBe("success");
  });

  it("refresh fallido tras éxito no cambia outcome", async () => {
    let items: MediaQueuedFile[] = [pendingItem("a")];
    const uploadAll = vi.fn(async () => {
      items = [{ ...pendingItem("a"), phase: "ready", archivoId: 1 }];
    });
    const result = await runManualMediaSave({
      rutaItemId: 3,
      uploadAll,
      getQueueItems: () => items,
      clearUploadedFromQueue: () => {
        items = [];
      },
      reloadServer: vi.fn(async () => {
        throw new Error("network");
      }),
    });
    expect(result.outcome).toBe("success");
    expect(result.refreshFailed).toBe(true);
  });

  it("fallo parcial no limpia cola", async () => {
    let items: MediaQueuedFile[] = [pendingItem("a"), pendingItem("b")];
    const uploadAll = vi.fn(async () => {
      items = [
        { ...pendingItem("a"), phase: "ready", archivoId: 1 },
        { ...pendingItem("b"), phase: "error", errorMessage: "Red" },
      ];
    });
    const clear = vi.fn();
    const result = await runManualMediaSave({
      rutaItemId: 4,
      uploadAll,
      getQueueItems: () => items,
      clearUploadedFromQueue: clear,
      reloadServer: vi.fn(),
    });
    expect(result.outcome).toBe("partial");
    expect(clear).not.toHaveBeenCalled();
  });

  it("countUploadableQueueItems ignora READY", () => {
    expect(
      countUploadableQueueItems([
        { ...pendingItem("a"), phase: "ready", archivoId: 1 },
      ])
    ).toBe(0);
  });
});
