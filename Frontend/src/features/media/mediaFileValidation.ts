import {
  MEDIA_ALLOWED_MIME,
  MEDIA_CATEGORY_MAX,
  MEDIA_MAX_IMAGE_BYTES,
  MEDIA_MAX_PDF_BYTES,
  type MediaCategoria1A,
} from "./mediaConstants";

export function maxBytesForMime(contentType: string): number {
  const ct = contentType.toLowerCase();
  if (ct === "application/pdf") return MEDIA_MAX_PDF_BYTES;
  return MEDIA_MAX_IMAGE_BYTES;
}

export function validateLocalMediaFile(
  file: File,
  categoria: MediaCategoria1A,
  currentCountInCategory: number
): string | null {
  const ct = (file.type || "").toLowerCase();
  if (!MEDIA_ALLOWED_MIME.has(ct)) {
    return "Tipo de archivo no permitido (solo JPEG, PNG, WebP o PDF).";
  }
  const maxBytes = maxBytesForMime(ct);
  if (file.size > maxBytes) {
    return ct === "application/pdf"
      ? "El PDF supera el máximo de 15 MB."
      : "La imagen supera el máximo de 10 MB.";
  }
  const maxItems = MEDIA_CATEGORY_MAX[categoria];
  if (currentCountInCategory >= maxItems) {
    return `Se alcanzó el máximo de ${maxItems} archivos para esta categoría.`;
  }
  return null;
}
