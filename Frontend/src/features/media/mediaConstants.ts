export const MEDIA_CATEGORIA_FOTO_ACTA = "FOTO_ACTA" as const;
export const MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL = "FOTO_DOCUMENTACION_LOCAL" as const;
export const MEDIA_CATEGORIA_FOTO_INSPECCION = "FOTO_INSPECCION" as const;

export type MediaCategoria =
  | typeof MEDIA_CATEGORIA_FOTO_ACTA
  | typeof MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL
  | typeof MEDIA_CATEGORIA_FOTO_INSPECCION;

/** Alias histórico: todas las galerías RutaItem (1A + 1B). */
export type MediaCategoria1A = MediaCategoria;

export const MEDIA_MAX_FOTO_ACTA = 7;
export const MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL = 9;
export const MEDIA_MAX_FOTO_INSPECCION = 12;

export const MEDIA_MAX_IMAGE_BYTES = 10_485_760;
export const MEDIA_MAX_PDF_BYTES = 15_728_640;

export const MEDIA_IMAGE_MIME = new Set(["image/jpeg", "image/png", "image/webp"]);

export const MEDIA_ALLOWED_MIME = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
]);

export const TIPOS_DOCUMENTO_FOTO_ACTA = [
  "ACTA_INSPECCION",
  "ACTA_NOTIFICACION",
  "OTRO_ACTA",
] as const;

export const TIPOS_DOCUMENTO_FOTO_LOCAL = [
  "HABILITACION",
  "CARNET_MANIPULADOR",
  "CERTIFICADO_DESINFECCION",
  "OTRO_DOCUMENTO_LOCAL",
] as const;

export const MEDIA_CATEGORY_LABELS: Record<MediaCategoria, string> = {
  [MEDIA_CATEGORIA_FOTO_ACTA]: "Fotos de las actas",
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]: "Fotos de la documentación del local",
  [MEDIA_CATEGORIA_FOTO_INSPECCION]: "Fotos de la inspección",
};

/** Texto orientativo bajo el título; no restringe tipos de archivo. */
export const MEDIA_CATEGORY_HINTS: Record<MediaCategoria, string> = {
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]:
    "Habilitación, carnet de desinfección, carnet de sanidad, remito de decomiso, etc.",
  [MEDIA_CATEGORIA_FOTO_ACTA]:
    "ODT, notificación, comprobación, decomiso, clausura, informe, faja, etc.",
  [MEDIA_CATEGORIA_FOTO_INSPECCION]:
    "Estado general, salón, cocina, depósito, baño, alimentos, equipos, irregularidades, etc.",
};

export const MEDIA_CATEGORY_MAX: Record<MediaCategoria, number> = {
  [MEDIA_CATEGORIA_FOTO_ACTA]: MEDIA_MAX_FOTO_ACTA,
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]: MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL,
  [MEDIA_CATEGORIA_FOTO_INSPECCION]: MEDIA_MAX_FOTO_INSPECCION,
};

/** Galerías de evidencia por RutaItem (orden de UI). */
export const MEDIA_RUTA_ITEM_GALLERIES = [
  {
    categoria: MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    titulo: "Fotos de la documentación del local",
    ejemplos: MEDIA_CATEGORY_HINTS[MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL],
    cupo: MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL,
  },
  {
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    titulo: "Fotos de las actas",
    ejemplos: MEDIA_CATEGORY_HINTS[MEDIA_CATEGORIA_FOTO_ACTA],
    cupo: MEDIA_MAX_FOTO_ACTA,
  },
  {
    categoria: MEDIA_CATEGORIA_FOTO_INSPECCION,
    titulo: "Fotos de la inspección",
    ejemplos: MEDIA_CATEGORY_HINTS[MEDIA_CATEGORIA_FOTO_INSPECCION],
    cupo: MEDIA_MAX_FOTO_INSPECCION,
  },
] as const;

/** @deprecated Usar MEDIA_RUTA_ITEM_GALLERIES */
export const MEDIA_1A_GALLERIES = MEDIA_RUTA_ITEM_GALLERIES;

export const MEDIA_CATEGORY_CONFIG_1A: Record<
  MediaCategoria,
  { categoria: MediaCategoria; titulo: string; ejemplos: string; cupo: number }
> = {
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]: {
    categoria: MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    titulo: MEDIA_CATEGORY_LABELS[MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL],
    ejemplos: MEDIA_CATEGORY_HINTS[MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL],
    cupo: MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL,
  },
  [MEDIA_CATEGORIA_FOTO_ACTA]: {
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    titulo: MEDIA_CATEGORY_LABELS[MEDIA_CATEGORIA_FOTO_ACTA],
    ejemplos: MEDIA_CATEGORY_HINTS[MEDIA_CATEGORIA_FOTO_ACTA],
    cupo: MEDIA_MAX_FOTO_ACTA,
  },
  [MEDIA_CATEGORIA_FOTO_INSPECCION]: {
    categoria: MEDIA_CATEGORIA_FOTO_INSPECCION,
    titulo: MEDIA_CATEGORY_LABELS[MEDIA_CATEGORIA_FOTO_INSPECCION],
    ejemplos: MEDIA_CATEGORY_HINTS[MEDIA_CATEGORIA_FOTO_INSPECCION],
    cupo: MEDIA_MAX_FOTO_INSPECCION,
  },
};

export function mediaAcceptAttributeForCategoria(categoria: MediaCategoria): string {
  if (categoria === MEDIA_CATEGORIA_FOTO_INSPECCION) {
    return "image/jpeg,image/png,image/webp";
  }
  return "image/jpeg,image/png,image/webp,application/pdf";
}
