import { describe, expect, it } from "vitest";
import { MEDIA_CATEGORY_LABELS, MEDIA_CATEGORY_MAX } from "./mediaConstants";
import { validateLocalMediaFile } from "./mediaFileValidation";
import type { MediaQueuedFile } from "./mediaTypes";
describe("MEDIA.1A categorías", () => {
  it("expone solo acta y documentación local (sin inspección)", () => {
    expect(Object.keys(MEDIA_CATEGORY_LABELS).sort()).toEqual([
      "FOTO_ACTA",
      "FOTO_DOCUMENTACION_LOCAL",
    ]);
    expect(MEDIA_CATEGORY_MAX.FOTO_ACTA).toBe(7);
    expect(MEDIA_CATEGORY_MAX.FOTO_DOCUMENTACION_LOCAL).toBe(9);
    expect("FOTO_INSPECCION" in MEDIA_CATEGORY_MAX).toBe(false);
  });
});

describe("cola local", () => {
  it("validateLocalMediaFile respeta cupo con serverCount implícito", () => {
    const file = new File(["x"], "a.jpg", { type: "image/jpeg" });
    for (let i = 0; i < 7; i++) {
      expect(validateLocalMediaFile(file, "FOTO_ACTA", i)).toBeNull();
    }
    expect(validateLocalMediaFile(file, "FOTO_ACTA", 7)).toMatch(/máximo/);
  });
});

describe("reintento de cola", () => {
  it("solo reintenta pending o error sin archivoId (READY no entra)", () => {
    const items: MediaQueuedFile[] = [
      {
        localId: "r1",
        file: new File(["x"], "b.jpg", { type: "image/jpeg" }),
        categoria: "FOTO_ACTA",
        tipoDocumento: null,
        phase: "ready",
        progressPct: 100,
        errorMessage: null,
        archivoId: 42,
        previewUrl: null,
      },
      {
        localId: "e1",
        file: new File(["y"], "c.jpg", { type: "image/jpeg" }),
        categoria: "FOTO_ACTA",
        tipoDocumento: null,
        phase: "error",
        progressPct: 0,
        errorMessage: "falló",
        archivoId: null,
        previewUrl: null,
      },
    ];
    const toUpload = items.filter(
      (x) => x.phase === "pending" || (x.phase === "error" && !x.archivoId)
    );
    expect(toUpload.map((x) => x.localId)).toEqual(["e1"]);
  });
});
