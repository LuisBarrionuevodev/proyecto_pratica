import { applyFormErrorsFromApi } from "../../../utils/parseApiError";
import { RELEVAMIENTO_ROW_ERROR_KEY_MAP } from "./submitRelevamientoRow";

const RELEVAMIENTO_FORM_OPTIONS = {
  fieldKeyAliases: RELEVAMIENTO_ROW_ERROR_KEY_MAP,
  fallbackMessage: "No se pudo guardar el relevamiento.",
} as const;

/**
 * Mapea errores API del PUT relevamiento a errores de campo + mensaje global (STAB-5).
 */
export function applyRelevamientoErrorsFromApi(err: unknown): {
  fieldErrors: Record<string, string>;
  globalMessage: string | null;
} {
  return applyFormErrorsFromApi(err, RELEVAMIENTO_FORM_OPTIONS);
}
