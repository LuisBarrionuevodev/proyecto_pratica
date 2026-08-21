import type { IRutaItemMin } from "../../../api/rutasTrabajoApi";

export type AsignacionContinuarMapaFinalState = {
  puedeContinuar: boolean;
  tooltip: string;
  itemsSinOtCount: number;
};

/**
 * Reglas de habilitación del CTA «Continuar a mapa final» (solo presentación; misma lógica que Asignación).
 */
export function computeAsignacionContinuarMapaFinal(
  totalEnPool: number,
  itemsActivos: IRutaItemMin[]
): AsignacionContinuarMapaFinalState {
  const itemsCount = itemsActivos.length;
  const hayTrabajoParaMapa = totalEnPool > 0 || itemsCount > 0;
  const itemsSinOt = itemsActivos.filter((it) => it.orden_trabajo_id == null);
  const puedeContinuar = hayTrabajoParaMapa && (itemsCount === 0 || itemsSinOt.length === 0);

  let tooltip = "Mapa operativo.";
  if (!hayTrabajoParaMapa) {
    tooltip = "Sin ítems en pool ni en la ruta.";
  } else if (itemsCount > 0 && itemsSinOt.length > 0) {
    tooltip = "Guardá la OT en cada ítem antes de continuar.";
  }

  return { puedeContinuar, tooltip, itemsSinOtCount: itemsSinOt.length };
}
