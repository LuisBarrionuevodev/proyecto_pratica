/** Mensaje corto para la card cuando la OT ya fue consumida por otra actuación. */
export const MENSAJE_OT_CONSUMIDA_CARD =
  "La OT ya fue utilizada en otra actuación. Aunque haya sido no realizada, esa OT queda consumida. Seleccioná una OT libre.";

export type RutaOtPatchErrorDebug = {
  validator?: string;
};

/**
 * Normaliza el mensaje de error del PATCH de OT para mostrar en la card del ítem.
 */
export function mensajeErrorGuardarOtPatch(
  detail: unknown,
  debug?: RutaOtPatchErrorDebug | null
): { message: string; otConsumida: boolean } {
  if (debug?.validator === "orden_trabajo_ocupada_por_otro_flujo") {
    return { message: MENSAJE_OT_CONSUMIDA_CARD, otConsumida: true };
  }
  if (typeof detail === "string" && detail.trim()) {
    return { message: detail.trim(), otConsumida: false };
  }
  return { message: "No se pudo guardar la OT", otConsumida: false };
}
