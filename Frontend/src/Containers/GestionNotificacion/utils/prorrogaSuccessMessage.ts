/** Mensaje de toast tras alta de expediente de prórroga (operativa / reinspección). */
export function prorrogaSuccessMessage(volvioEnPlazo: boolean): string {
  return volvioEnPlazo
    ? "Prórroga registrada. La notificación volvió a estar en plazo."
    : "Prórroga registrada correctamente.";
}

export function volvioEnPlazoDesdeExpedienteMeta(
  nextStateHint: string | undefined | null
): boolean {
  return nextStateHint === "EN_PLAZO";
}

export type GuardarProrrogaResult = { ok: true; volvioEnPlazo: boolean } | { ok: false };
