import { mapCrudApiErrorsToFormState } from "../../../components/crudDialog/crudFormErrors";
import type { FormErrorsFromApi } from "../../../utils/parseApiError";

function extractApiDetail(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }
  return "";
}

/** Heurística legacy para errores de usuarios cuando el backend solo envía `detail`. */
function mapUsuarioDetailToFieldErrors(detail: string): Record<string, string> {
  const mapped: Record<string, string> = {};
  const detailLower = detail.toLowerCase();
  if (detailLower.includes("email")) {
    mapped.email = detail || "Email ya está en uso.";
  }
  if (detailLower.includes("username") || detailLower.includes("usuario")) {
    mapped.username = detail || "Username ya está en uso.";
  }
  if (detailLower.includes("rol") || detailLower.includes("role")) {
    mapped.role = detail || "Rol inválido.";
  }
  return mapped;
}

/**
 * Mapea errores API de alta/edición de usuario a campos + resumen global (CRUD glass).
 */
export function mapGestionUsuarioApiErrors(
  err: unknown,
  fallbackMessage: string
): FormErrorsFromApi {
  const parsed = mapCrudApiErrorsToFormState(err, { fallbackMessage });
  if (Object.keys(parsed.fieldErrors).length > 0) {
    return {
      fieldErrors: parsed.fieldErrors,
      globalMessage: null,
    };
  }

  const detail = extractApiDetail(err);
  const fromDetail = detail ? mapUsuarioDetailToFieldErrors(detail) : {};
  if (Object.keys(fromDetail).length > 0) {
    return {
      fieldErrors: fromDetail,
      globalMessage: null,
    };
  }

  return {
    fieldErrors: {},
    globalMessage: parsed.globalMessage ?? fallbackMessage,
  };
}
