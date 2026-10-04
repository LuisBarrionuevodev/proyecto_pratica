/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as mediaApi from "../../api/mediaApi";
import { MEDIA_CATEGORY_HINTS, MEDIA_CATEGORY_LABELS } from "./mediaConstants";
import { MediaUploadSection } from "./components/MediaUploadSection";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "./mediaConstants";
import type { MediaQueuedFile } from "./mediaTypes";

const theme = createTheme();

describe("HOTFIX MEDIA.1A.1", () => {
  it("encabezados y ejemplos exactos", () => {
    expect(MEDIA_CATEGORY_LABELS.FOTO_DOCUMENTACION_LOCAL).toBe("Fotos de la documentación del local");
    expect(MEDIA_CATEGORY_HINTS.FOTO_DOCUMENTACION_LOCAL).toBe(
      "Habilitación, carnet de desinfección, carnet de sanidad, remito de decomiso, etc."
    );
    expect(MEDIA_CATEGORY_LABELS.FOTO_ACTA).toBe("Fotos de las actas");
    expect(MEDIA_CATEGORY_HINTS.FOTO_ACTA).toBe(
      "ODT, notificación, comprobación, decomiso, clausura, informe, faja, etc."
    );
    expect(MEDIA_CATEGORY_HINTS.FOTO_ACTA).toContain("comprobación");
    expect(MEDIA_CATEGORY_HINTS.FOTO_ACTA).not.toMatch(/comprobante/i);
  });

  it("no renderiza selector de tipo documental y usa botones primary/danger", () => {
    const pending: MediaQueuedFile = {
      localId: "p1",
      file: new File(["x"], "foto.jpg", { type: "image/jpeg" }),
      categoria: MEDIA_CATEGORIA_FOTO_ACTA,
      tipoDocumento: null,
      phase: "pending",
      progressPct: 0,
      errorMessage: null,
      archivoId: null,
      previewUrl: null,
    };
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <MediaUploadSection
          categoria="FOTO_ACTA"
          items={[pending]}
          onAddFiles={() => undefined}
          onRemove={() => undefined}
        />
      </ThemeProvider>
    );
    expect(html).not.toContain("Tipo de documento");
    expect(html).toContain("Seleccionar archivos");
    expect(html).toContain("MuiButton-containedPrimary");
    expect(html).toContain("Quitar");
    expect(html).toContain("MuiButton-containedError");
    expect(html).toContain(MEDIA_CATEGORY_HINTS.FOTO_ACTA);
  });

  it("upload-intent sin tipo_documento", async () => {
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
    const intentSpy = vi.spyOn(mediaApi, "postMediaUploadIntent").mockResolvedValue({
      archivo_id: 3,
      upload_url: "mock://put/x",
      expires_at: "2026-01-01T00:00:00Z",
    });
    vi.spyOn(mediaApi, "postMediaComplete").mockResolvedValue({ archivo_id: 3, status: "READY" });
    const { uploadSingleQueuedFile } = await import("./mediaUploadPipeline");
    const file = new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" });
    await uploadSingleQueuedFile(1, {
      localId: "1",
      file,
      categoria: MEDIA_CATEGORIA_FOTO_ACTA,
      tipoDocumento: null,
      phase: "pending",
      progressPct: 0,
      errorMessage: null,
      archivoId: null,
      previewUrl: null,
    });
    const body = intentSpy.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(body).toBeDefined();
    expect(body.categoria).toBe("FOTO_ACTA");
    expect("tipo_documento" in body).toBe(false);
    vi.unstubAllGlobals();
  });
});
