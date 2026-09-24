import { subtipoOficioEsVerificar } from "./reinspeccionOficioSubtipo";
import type { VerificarEstadoOperativo } from "./verificarEstadoOperativo";

/** Contexto de validación CRUD para reinspección por oficio (estado destino del formulario). */
export type ReinspeccionOficioValidationContextInput = {
  subtipo: string;
  verificarEstadoOperativo: VerificarEstadoOperativo;
};

/**
 * True solo cuando el subtipo destino es Verificar e Informar con nueva inspección (SI_INSPECCION).
 * Goberna render, validación y creación de actas de inspección normal en reinspección por oficio.
 */
export function usaInspeccionNormalReinspeccionOficio(
  subtipo: string | null | undefined,
  verificarEstadoOperativo: VerificarEstadoOperativo | null | undefined
): boolean {
  if (!subtipoOficioEsVerificar(subtipo)) return false;
  return verificarEstadoOperativo === "SI_INSPECCION";
}
