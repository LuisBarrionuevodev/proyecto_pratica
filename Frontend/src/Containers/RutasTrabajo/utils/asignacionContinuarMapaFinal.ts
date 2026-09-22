import type { IRutaItemMin } from "../../../api/rutasTrabajoApi";

export type AsignacionContinuarMapaFinalState = {
  puedeContinuar: boolean;
  tooltip: string;
};

/**
 * Reglas de habilitación del CTA «Continuar a mapa final» (OT-AUTO: OT ya no es requisito).
 */
export function computeAsignacionContinuarMapaFinal(
  totalEnPool: number,
  itemsActivos: IRutaItemMin[]
): AsignacionContinuarMapaFinalState {
  const itemsCount = itemsActivos.length;
  const hayTrabajoParaMapa = totalEnPool > 0 || itemsCount > 0;
  const puedeContinuar = hayTrabajoParaMapa;

  let tooltip = "Mapa operativo.";
  if (!hayTrabajoParaMapa) {
    tooltip = "Sin ítems en pool ni en la ruta.";
  }

  return { puedeContinuar, tooltip };
}
