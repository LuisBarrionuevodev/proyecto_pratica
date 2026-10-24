import { isAxiosError } from "axios";

import {
  MEDIA_STATE_INVALID_RETRY_MESSAGE,
  MEDIA_UPLOAD_GENERIC_FAILURE_MESSAGE,
} from "./utils/mediaUploadMessages";

const MESSAGES: Record<string, string> = {
  MEDIA_QUOTA_EXCEEDED: "Se alcanzó el cupo de archivos para esta categoría.",
  MEDIA_MIME_UNSUPPORTED: "Tipo de archivo no permitido.",
  MEDIA_SIZE_EXCEEDED: "El archivo supera el tamaño máximo permitido.",
  MEDIA_OBJECT_MISSING: "No se encontró el archivo en el servidor. Reintentá la subida.",
  MEDIA_SHA_MISMATCH: "El archivo cambió durante la carga. Seleccioná el archivo otra vez.",
  MEDIA_STATE_INVALID: MEDIA_STATE_INVALID_RETRY_MESSAGE,
};

/**
 * Mensaje operativo a partir de error HTTP de Media.
 */
function isLikelyNetworkAxiosError(error: unknown): boolean {
  if (!isAxiosError(error)) return false;
  if (error.response) return false;
  const code = error.code;
  return code === "ERR_NETWORK" || code === "ECONNABORTED";
}

export function mediaErrorMessageFromUnknown(error: unknown): string {
  if (isAxiosError(error)) {
    const data = error.response?.data as { code?: string; detail?: string } | undefined;
    if (data?.code && MESSAGES[data.code]) {
      return MESSAGES[data.code];
    }
    if (data?.detail && typeof data.detail === "string") {
      return data.detail;
    }
    if (isLikelyNetworkAxiosError(error)) {
      return "Error de red al subir el archivo.";
    }
    if (error.response) {
      return MEDIA_UPLOAD_GENERIC_FAILURE_MESSAGE;
    }
  }
  if (error instanceof Error && error.message) {
    const lower = error.message.toLowerCase();
    if (lower.includes("error de red")) {
      return error.message;
    }
    if (lower.includes("network error")) {
      return "Error de red al subir el archivo.";
    }
    return error.message;
  }
  return MEDIA_UPLOAD_GENERIC_FAILURE_MESSAGE;
}
