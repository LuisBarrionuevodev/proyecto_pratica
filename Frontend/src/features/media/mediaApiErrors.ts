import { isAxiosError } from "axios";

import {
  MEDIA_STATE_INVALID_RETRY_MESSAGE,
  MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE,
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

function collectErrorTextParts(error: unknown): { names: string[]; messages: string[] } {
  const names: string[] = [];
  const messages: string[] = [];
  const seen = new Set<unknown>();
  let current: unknown = error;
  for (let i = 0; i < 4 && current != null && !seen.has(current); i++) {
    seen.add(current);
    if (typeof current === "string") {
      messages.push(current);
      break;
    }
    if (typeof current !== "object") break;
    const rec = current as { name?: unknown; message?: unknown; code?: unknown; cause?: unknown };
    if (typeof rec.name === "string" && rec.name) names.push(rec.name);
    if (typeof rec.message === "string" && rec.message) messages.push(rec.message);
    if (typeof rec.code === "string" && rec.code) names.push(rec.code);
    current = rec.cause;
  }
  return { names, messages };
}

/**
 * Referencia temporal de Google Fotos / File no legible: reintentar el mismo File no sirve.
 */
export function isMediaUnreadableLocalFileError(error: unknown): boolean {
  if (typeof error === "string") {
    return isMediaUnreadableLocalFileMessage(error);
  }
  const { names, messages } = collectErrorTextParts(error);
  if (names.some((n) => n.toLowerCase() === "notreadableerror")) return true;
  return messages.some((m) => isMediaUnreadableLocalFileMessage(m));
}

export function isMediaUnreadableLocalFileMessage(text: string | null | undefined): boolean {
  if (!text) return false;
  if (text === MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE) return true;
  const lower = text.toLowerCase();
  if (lower.includes("notreadableerror")) return true;
  if (lower.includes("the requested file could not be read")) return true;
  if (lower.includes("could not be read") && lower.includes("permission")) return true;
  if (lower.includes("permission problems") && lower.includes("reference to a file")) return true;
  return false;
}

/**
 * Mensaje operativo a partir de error HTTP de Media o fallo local de lectura.
 */
function isLikelyNetworkAxiosError(error: unknown): boolean {
  if (!isAxiosError(error)) return false;
  if (error.response) return false;
  const code = error.code;
  return code === "ERR_NETWORK" || code === "ECONNABORTED";
}

export function mediaErrorMessageFromUnknown(error: unknown): string {
  if (isMediaUnreadableLocalFileError(error)) {
    return MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE;
  }
  if (isAxiosError(error)) {
    const data = error.response?.data as { code?: string; detail?: string } | undefined;
    if (data?.code && MESSAGES[data.code]) {
      return MESSAGES[data.code];
    }
    if (data?.detail && typeof data.detail === "string") {
      if (isMediaUnreadableLocalFileMessage(data.detail)) {
        return MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE;
      }
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
