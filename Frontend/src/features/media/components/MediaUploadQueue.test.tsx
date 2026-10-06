import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MediaUploadQueue } from "./MediaUploadQueue";
import type { MediaQueuedFile } from "../mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";

function item(phase: MediaQueuedFile["phase"]): MediaQueuedFile {
  return {
    localId: "mq-1",
    file: new File(["x"], "foto.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase,
    progressPct: 0,
    errorMessage: phase === "error" ? "Red" : null,
    archivoId: null,
    previewUrl: null,
  };
}

describe("MediaUploadQueue", () => {
  it("sin onRetry no muestra botón Reintentar en error", () => {
    const html = renderToStaticMarkup(
      <MediaUploadQueue items={[item("error")]} onRemove={vi.fn()} />
    );
    expect(html).not.toMatch(/Reintentar/i);
    expect(html).toMatch(/No se pudo subir/i);
  });

  it("con onRetry muestra Reintentar en error", () => {
    const html = renderToStaticMarkup(
      <MediaUploadQueue items={[item("error")]} onRemove={vi.fn()} onRetry={vi.fn()} />
    );
    expect(html).toMatch(/Reintentar/i);
  });
});
