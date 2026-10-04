import { describe, expect, it, vi } from "vitest";
import * as mediaApi from "../../api/mediaApi";
import { putFileToPresignedUrl } from "./mediaUploadPipeline";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "./mediaConstants";
import type { MediaQueuedFile } from "./mediaTypes";

describe("putFileToPresignedUrl", () => {
  it("usa XMLHttpRequest PUT", async () => {
    const open = vi.fn();
    const sent: unknown[] = [];
    const setHeader = vi.fn();
    class MockXHR {
      upload = { onprogress: null as ((ev: ProgressEvent) => void) | null };
      status = 200;
      open = open;
      setRequestHeader = setHeader;
      send = vi.fn(function (this: MockXHR, body: unknown) {
        sent.push(body);
        queueMicrotask(() => this.onload?.());
      });
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
    }
    vi.stubGlobal("XMLHttpRequest", MockXHR);
    const file = new File(["x"], "a.pdf", { type: "application/pdf" });
    await putFileToPresignedUrl("mock://put/x", file, "application/pdf");
    expect(open).toHaveBeenCalledWith("PUT", "mock://put/x", true);
    expect(sent[0]).toBe(file);
    vi.unstubAllGlobals();
  });
});

describe("upload flow contract", () => {
  it("uploadSingleQueuedFile llama intent, complete y PUT", async () => {
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
    vi.spyOn(mediaApi, "postMediaUploadIntent").mockResolvedValue({
      archivo_id: 9,
      upload_url: "mock://put/bucket/key?ct=application/pdf",
      expires_at: "2026-01-01T00:00:00Z",
    });
    vi.spyOn(mediaApi, "postMediaComplete").mockResolvedValue({ archivo_id: 9, status: "READY" });
    const { uploadSingleQueuedFile } = await import("./mediaUploadPipeline");
    const file = new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" });
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
    const res = await uploadSingleQueuedFile(1, item);
    expect(res.archivoId).toBe(9);
    expect(mediaApi.postMediaUploadIntent).toHaveBeenCalled();
    const body = vi.mocked(mediaApi.postMediaUploadIntent).mock.calls[0]?.[1] as Record<string, unknown>;
    expect(body).toBeDefined();
    expect("tipo_documento" in body).toBe(false);
    expect(mediaApi.postMediaComplete).toHaveBeenCalledWith(9);
    vi.unstubAllGlobals();
  });
});
