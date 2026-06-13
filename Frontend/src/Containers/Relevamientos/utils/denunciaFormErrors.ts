import { applyFormErrorsFromApi } from "../../../utils/parseApiError";

const DENUNCIA_FORM_OPTIONS = {
  fallbackMessage: "No se pudo actualizar la denuncia.",
} as const;

/**
 * Mapea errores API del PUT denuncia a errores de campo + mensaje global (STAB-5).
 */
export function applyDenunciaErrorsFromApi(err: unknown): {
  fieldErrors: Record<string, string>;
  globalMessage: string | null;
} {
  return applyFormErrorsFromApi(err, DENUNCIA_FORM_OPTIONS);
}
