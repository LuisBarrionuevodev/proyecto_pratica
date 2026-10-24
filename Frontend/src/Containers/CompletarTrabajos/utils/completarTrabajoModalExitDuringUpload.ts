/**
 * Política de cierre del modal Completar trabajo mientras corre una sesión de subida (MEDIA.2E.1A).
 */

export type CompletarTrabajoModalClosePolicyInput = {
  saving: boolean;
  mediaSessionActive: boolean;
  finalizingPorAhora: boolean;
};

/** Bloquea el intento de cierre (sin diálogo). */
export function shouldBlockCompletarTrabajoModalClose(
  input: CompletarTrabajoModalClosePolicyInput
): boolean {
  if (input.finalizingPorAhora) return true;
  if (input.saving && !input.mediaSessionActive) return true;
  return false;
}

/** Muestra confirmación Continuar subiendo / Salir y pausar subida. */
export function shouldConfirmPauseMediaUploadOnClose(mediaSessionActive: boolean): boolean {
  return mediaSessionActive;
}
