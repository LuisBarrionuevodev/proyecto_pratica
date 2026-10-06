import { isAxiosError } from "axios";

const MESSAGES: Record<string, string> = {
  MEDIA_QUOTA_EXCEEDED: "Se alcanzó el cupo de archivos para esta categoría.",
  MEDIA_MIME_UNSUPPORTED: "Tipo de archivo no permitido.",
  MEDIA_SIZE_EXCEEDED: "El archivo supera el tamaño máximo permitido.",
  MEDIA_OBJECT_MISSING: "No se encontró el archivo en el servidor. Reintentá la subida.",
  MEDIA_SHA_MISMATCH: "El archivo cambió durante la carga. Seleccioná el archivo otra vez.",
  MEDIA_STATE_INVALID: "No se pudo completar la carga en este momento.",
};

/**
 * Mensaje operativo a partir de error HTTP de Media.
 */
export function mediaErrorMessageFromUnknown(error: unknown): string {
  if (isAxiosError(error)) {
    const data = error.response?.data as { code?: string; detail?: string } | undefined;
    if (data?.code && MESSAGES[data.code]) {
      return MESSAGES[data.code];
    }
    if (data?.detail && typeof data.detail === "string") {
      return data.detail;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "No se pudo subir el archivo.";
}
