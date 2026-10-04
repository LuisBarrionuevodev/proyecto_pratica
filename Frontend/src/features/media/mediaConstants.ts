export const MEDIA_CATEGORIA_FOTO_ACTA = "FOTO_ACTA" as const;
export const MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL = "FOTO_DOCUMENTACION_LOCAL" as const;
export const MEDIA_CATEGORIA_FOTO_INSPECCION = "FOTO_INSPECCION" as const;

export type MediaCategoria1A =
  | typeof MEDIA_CATEGORIA_FOTO_ACTA
  | typeof MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL;

export const MEDIA_MAX_FOTO_ACTA = 7;
export const MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL = 9;

export const MEDIA_MAX_IMAGE_BYTES = 10_485_760;
export const MEDIA_MAX_PDF_BYTES = 15_728_640;

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

export const MEDIA_CATEGORY_LABELS: Record<MediaCategoria1A, string> = {
  [MEDIA_CATEGORIA_FOTO_ACTA]: "Fotos de las actas",
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]: "Fotos de la documentación del local",
};

/** Texto orientativo bajo el título; no restringe tipos de archivo. */
export const MEDIA_CATEGORY_HINTS: Record<MediaCategoria1A, string> = {
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]:
    "Habilitación, carnet de desinfección, carnet de sanidad, remito de decomiso, etc.",
  [MEDIA_CATEGORIA_FOTO_ACTA]:
    "ODT, notificación, comprobación, decomiso, clausura, informe, faja, etc.",
};

export const MEDIA_CATEGORY_MAX: Record<MediaCategoria1A, number> = {
  [MEDIA_CATEGORIA_FOTO_ACTA]: MEDIA_MAX_FOTO_ACTA,
  [MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL]: MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL,
};

/** Configuración por galería (extensible a Media.1B). */
export const MEDIA_CATEGORY_CONFIG_1A: Record<
  MediaCategoria1A,
  { categoria: MediaCategoria1A; titulo: string; ejemplos: string; cupo: number }
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
};
