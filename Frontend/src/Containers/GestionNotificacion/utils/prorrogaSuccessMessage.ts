/** Mensaje de toast tras alta de expediente de prórroga (operativa / reinspección). */
export function prorrogaAltaSuccessMessage(volvioEnPlazo: boolean): string {
  if (volvioEnPlazo) {
    return "Expediente registrado correctamente. La notificación volvió a estar en plazo.";
  }
  return "Expediente registrado correctamente.";
}

export const EXPEDIENTE_ACTUALIZADO_MSG = "Expediente actualizado correctamente.";
export const EXPEDIENTE_ELIMINADO_MSG = "Expediente eliminado correctamente.";

/** @deprecated Usar prorrogaAltaSuccessMessage */
export function prorrogaSuccessMessage(volvioEnPlazo: boolean): string {
  return prorrogaAltaSuccessMessage(volvioEnPlazo);
}

export function volvioEnPlazoDesdeExpedienteMeta(
  nextStateHint: string | undefined | null
): boolean {
  return nextStateHint === "EN_PLAZO";
}

export type GuardarProrrogaResult = { ok: true; volvioEnPlazo: boolean } | { ok: false };
