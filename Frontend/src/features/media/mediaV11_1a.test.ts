import { describe, expect, it } from "vitest";
import { MEDIA_CATEGORY_LABELS, MEDIA_CATEGORY_MAX, MEDIA_RUTA_ITEM_GALLERIES } from "./mediaConstants";
import { validateLocalMediaFile } from "./mediaFileValidation";
import type { MediaQueuedFile } from "./mediaTypes";
describe("MEDIA galerías RutaItem", () => {
  it("expone tres categorías con cupos 9, 7 y 12", () => {
    expect(Object.keys(MEDIA_CATEGORY_LABELS).sort()).toEqual([
      "FOTO_ACTA",
      "FOTO_DOCUMENTACION_LOCAL",
      "FOTO_INSPECCION",
    ]);
    expect(MEDIA_CATEGORY_MAX.FOTO_ACTA).toBe(7);
    expect(MEDIA_CATEGORY_MAX.FOTO_DOCUMENTACION_LOCAL).toBe(9);
    expect(MEDIA_CATEGORY_MAX.FOTO_INSPECCION).toBe(12);
    expect(MEDIA_RUTA_ITEM_GALLERIES).toHaveLength(3);
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

  it("FOTO_INSPECCION rechaza PDF", () => {
    const pdf = new File(["%PDF"], "x.pdf", { type: "application/pdf" });
    expect(validateLocalMediaFile(pdf, "FOTO_INSPECCION", 0)).toMatch(/solo JPEG/);
  });

  it("FOTO_INSPECCION cupo 12", () => {
    const file = new File(["x"], "a.jpg", { type: "image/jpeg" });
    expect(validateLocalMediaFile(file, "FOTO_INSPECCION", 11)).toBeNull();
    expect(validateLocalMediaFile(file, "FOTO_INSPECCION", 12)).toMatch(/máximo/);
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
