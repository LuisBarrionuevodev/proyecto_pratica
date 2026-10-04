import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

import { getSemanticColors } from "../../theme/colors";
import { mediaUploadProgressDialogPaperSx } from "./mediaUploadProgressPanelStyles";
import * as mediaApi from "../../api/mediaApi";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "./mediaConstants";
import type { MediaQueuedFile } from "./mediaTypes";

const root = join(dirname(fileURLToPath(import.meta.url)), "../..");

function readSrc(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

describe("MEDIA.2 panel de progreso", () => {
  it("usa superficie sólida sin backdrop-filter", () => {
    const light = mediaUploadProgressDialogPaperSx("light");
    const dark = mediaUploadProgressDialogPaperSx("dark");
    expect(light).toMatchObject({ backdropFilter: "none" });
    expect(dark).toMatchObject({ backdropFilter: "none" });
    const c = getSemanticColors("light");
    expect(light).toMatchObject({ backgroundColor: c.surface.tableRowEven });
  });

  it("MediaUploadProgress no importa GLASS_COLORS", () => {
    const src = readSrc("features/media/components/MediaUploadProgress.tsx");
    expect(src).not.toContain("GLASS_COLORS");
    expect(src).toContain("mediaUploadProgressDialogPaperSx");
  });
});

describe("MEDIA.2 reintento", () => {
  it("uploadSingleQueuedFile pide intent nuevo en cada intento", async () => {
    class MockXHR {
      upload = { onprogress: null as ((ev: ProgressEvent) => void) | null };
      status = 200;
      open = vi.fn();
      setRequestHeader = vi.fn();
      send = vi.fn(function (this: MockXHR) {
        queueMicrotask(() => this.onload?.());
      });
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
    }
    vi.stubGlobal("XMLHttpRequest", MockXHR);
    const intentSpy = vi
      .spyOn(mediaApi, "postMediaUploadIntent")
      .mockResolvedValueOnce({
        archivo_id: 1,
        upload_url: "mock://put/a",
        expires_at: "2026-01-01T00:00:00Z",
      })
      .mockResolvedValueOnce({
        archivo_id: 2,
        upload_url: "mock://put/b",
        expires_at: "2026-01-01T00:00:00Z",
      });
    vi.spyOn(mediaApi, "postMediaComplete").mockResolvedValue({ archivo_id: 2, status: "READY" });
    const { uploadSingleQueuedFile } = await import("./mediaUploadPipeline");
    const file = new File(["x"], "a.jpg", { type: "image/jpeg" });
    const item: MediaQueuedFile = {
      localId: "1",
      file,
      categoria: MEDIA_CATEGORIA_FOTO_ACTA,
      tipoDocumento: null,
      phase: "pending",
      progressPct: 0,
      errorMessage: null,
      archivoId: null,
      previewUrl: null,
    };
    await uploadSingleQueuedFile(1, item);
    await uploadSingleQueuedFile(1, item);
    expect(intentSpy).toHaveBeenCalledTimes(2);
    vi.unstubAllGlobals();
  });
});
