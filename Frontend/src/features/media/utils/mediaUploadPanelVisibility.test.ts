import { describe, expect, it } from "vitest";
import type { MediaQueuedFile } from "../mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";
import { resolveMediaUploadPanelPhase } from "./mediaUploadPanelVisibility";

function item(phase: MediaQueuedFile["phase"]): MediaQueuedFile {
  return {
    localId: "1",
    file: new File(["x"], "a.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase,
    progressPct: 0,
    errorMessage: phase === "error" ? "Red" : null,
    archivoId: null,
    previewUrl: null,
  };
}

describe("mediaUploadPanelVisibility", () => {
  it("detecta éxito cuando todos ready y sesión inactiva", () => {
    expect(
      resolveMediaUploadPanelPhase(false, [item("ready"), item("ready")])
    ).toBe("success");
  });

  it("detecta corte con fotos parciales", () => {
    expect(
      resolveMediaUploadPanelPhase(false, [item("ready"), item("error")])
    ).toBe("interrupted");
  });
});
