import { describe, expect, it } from "vitest";
import {
  MEDIA_CATEGORY_LABELS,
  MEDIA_CATEGORY_MAX,
  MEDIA_INPUT_ACCEPT,
  MEDIA_RUTA_ITEM_GALLERIES,
  mediaAcceptAttributeForCategoria,
} from "./mediaConstants";
import { validateLocalMediaFile } from "./mediaFileValidation";
import type { MediaQueuedFile } from "./mediaTypes";
describe("MEDIA galerías RutaItem", () => {
  it("expone tres categorías con cupos 10, 10 y 20", () => {
    expect(Object.keys(MEDIA_CATEGORY_LABELS).sort()).toEqual([
      "FOTO_ACTA",
      "FOTO_DOCUMENTACION_LOCAL",
      "FOTO_INSPECCION",
    ]);
    expect(MEDIA_CATEGORY_MAX.FOTO_ACTA).toBe(10);
    expect(MEDIA_CATEGORY_MAX.FOTO_DOCUMENTACION_LOCAL).toBe(10);
    expect(MEDIA_CATEGORY_MAX.FOTO_INSPECCION).toBe(20);
    expect(MEDIA_RUTA_ITEM_GALLERIES).toHaveLength(3);
  });
});

describe("cola local", () => {
  it("validateLocalMediaFile respeta cupo con serverCount implícito", () => {
    const file = new File(["x"], "a.jpg", { type: "image/jpeg" });
    for (let i = 0; i < 10; i++) {
      expect(validateLocalMediaFile(file, "FOTO_ACTA", i)).toBeNull();
    }
    expect(validateLocalMediaFile(file, "FOTO_ACTA", 10)).toMatch(/máximo/);
  });

  it("FOTO_INSPECCION rechaza PDF", () => {
    const pdf = new File(["%PDF"], "x.pdf", { type: "application/pdf" });
    expect(validateLocalMediaFile(pdf, "FOTO_INSPECCION", 0)).toBe(
      "Tipo de archivo no permitido (solo JPEG, PNG o WebP)."
    );
  });

  it("FOTO_INSPECCION acepta JPG, PNG y WebP", () => {
    expect(validateLocalMediaFile(new File(["x"], "a.jpg", { type: "image/jpeg" }), "FOTO_INSPECCION", 0)).toBeNull();
    expect(validateLocalMediaFile(new File(["x"], "a.png", { type: "image/png" }), "FOTO_INSPECCION", 0)).toBeNull();
    expect(validateLocalMediaFile(new File(["x"], "a.webp", { type: "image/webp" }), "FOTO_INSPECCION", 0)).toBeNull();
  });

  it("Documentación y Actas siguen permitiendo PDF", () => {
    const pdf = new File(["%PDF"], "x.pdf", { type: "application/pdf" });
    expect(validateLocalMediaFile(pdf, "FOTO_ACTA", 0)).toBeNull();
    expect(validateLocalMediaFile(pdf, "FOTO_DOCUMENTACION_LOCAL", 0)).toBeNull();
  });

  it("las tres galerías usan el mismo accept nativo (incluye PDF)", () => {
    expect(mediaAcceptAttributeForCategoria("FOTO_INSPECCION")).toBe(MEDIA_INPUT_ACCEPT);
    expect(mediaAcceptAttributeForCategoria("FOTO_ACTA")).toBe(MEDIA_INPUT_ACCEPT);
    expect(mediaAcceptAttributeForCategoria("FOTO_DOCUMENTACION_LOCAL")).toBe(MEDIA_INPUT_ACCEPT);
    expect(MEDIA_INPUT_ACCEPT).toBe("image/jpeg,image/png,image/webp,application/pdf");
  });

  it("FOTO_INSPECCION cupo 20", () => {
    const file = new File(["x"], "a.jpg", { type: "image/jpeg" });
    expect(validateLocalMediaFile(file, "FOTO_INSPECCION", 19)).toBeNull();
    expect(validateLocalMediaFile(file, "FOTO_INSPECCION", 20)).toMatch(/máximo/);
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
