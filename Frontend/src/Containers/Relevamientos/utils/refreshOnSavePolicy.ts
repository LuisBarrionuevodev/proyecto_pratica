import type { SubmitRelevamientoRowResult } from "./submitRelevamientoRow";
import { isApiValidationError } from "../../../utils/parseApiError";

/**
 * Tras un guardado fallido de relevamiento, indica si conviene refetch de la bandeja.
 */
export function shouldRefreshRelevamientosAfterSaveFailure(
  result: SubmitRelevamientoRowResult
): boolean {
  if (result.ok) return true;
  if (result.kind === "validation" || result.kind === "backend_fields") return false;
  return false;
}

/**
 * Tras un guardado fallido de denuncia, indica si conviene refetch de la bandeja.
 */
export function shouldRefreshDenunciasAfterSaveFailure(
  err: unknown,
  fieldErrors: Record<string, string>
): boolean {
  if (Object.keys(fieldErrors).length > 0) return false;
  if (isApiValidationError(err)) return false;
  return false;
}
