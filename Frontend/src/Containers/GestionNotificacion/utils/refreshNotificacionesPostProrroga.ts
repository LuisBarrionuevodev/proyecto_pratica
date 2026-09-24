import type { OperativaNotificacionFiltroPayload } from "./buildOperativaNotificacionFiltroPayload";
import type { OperativaNotificacionSlice } from "./operativaNotificacionBaseCache";
import type { OperativePlazoExpedienteSlice, PlazoOperativoSlice } from "../gestionNotificacionPlazo";

export type RefreshNotificacionesPostProrrogaContext = {
  activeSlice: PlazoOperativoSlice;
  invalidateOperativaBaseTabs: (slices: OperativaNotificacionSlice[]) => void;
  loadPlazoSlice: (
    slice: OperativePlazoExpedienteSlice,
    filters: OperativaNotificacionFiltroPayload | null,
    opts?: { silent?: boolean; forceBaseRefresh?: boolean }
  ) => Promise<void>;
  loadReinspeccion: (
    filters: OperativaNotificacionFiltroPayload | null,
    opts?: { silent?: boolean; forceBaseRefresh?: boolean }
  ) => Promise<void>;
};

/** Tras expediente/prórroga desde bandejas de plazo. */
export const MUTATION_INVALIDATE_PLAZO: OperativaNotificacionSlice[] = ["en_plazo", "por_vencer"];

/** Tras pool/ruta/completar trabajo en reinspección. */
export const MUTATION_INVALIDATE_REINSPECCION: OperativaNotificacionSlice[] = ["reinspeccion"];

/** Tras sync vencidas o mutación que afecta las tres bandejas operativas. */
export const MUTATION_INVALIDATE_ALL_OPERATIVE: OperativaNotificacionSlice[] = [
  "en_plazo",
  "por_vencer",
  "reinspeccion",
];

/**
 * Determina qué snapshots invalidar tras alta/edición/eliminación de expediente o prórroga.
 * Desde reinspección puede mover ítems hacia bandejas de plazo.
 */
export function resolveNotificacionMutationInvalidateTabs(
  activeSlice: PlazoOperativoSlice,
  fromReinspeccionModal: boolean
): OperativaNotificacionSlice[] {
  if (activeSlice === "vencidas_o_hoy" || fromReinspeccionModal) {
    return MUTATION_INVALIDATE_ALL_OPERATIVE;
  }
  return MUTATION_INVALIDATE_PLAZO;
}

/**
 * Refresca slices operativos tras mutación.
 * Invalida solo los snapshots indicados y recarga dataset base (sin filtros).
 * El slice activo muestra loader; el resto se sincroniza en silencio.
 */
export async function refreshNotificacionesPostProrroga(
  ctx: RefreshNotificacionesPostProrrogaContext,
  invalidatedSlices: OperativaNotificacionSlice[]
): Promise<void> {
  if (invalidatedSlices.length === 0) return;
  ctx.invalidateOperativaBaseTabs(invalidatedSlices);
  const { activeSlice } = ctx;
  const tasks: Promise<void>[] = [];
  if (invalidatedSlices.includes("en_plazo")) {
    tasks.push(
      ctx.loadPlazoSlice("en_plazo", null, {
        silent: activeSlice !== "en_plazo",
        forceBaseRefresh: true,
      })
    );
  }
  if (invalidatedSlices.includes("por_vencer")) {
    tasks.push(
      ctx.loadPlazoSlice("por_vencer", null, {
        silent: activeSlice !== "por_vencer",
        forceBaseRefresh: true,
      })
    );
  }
  if (invalidatedSlices.includes("reinspeccion")) {
    tasks.push(
      ctx.loadReinspeccion(null, {
        silent: activeSlice !== "vencidas_o_hoy",
        forceBaseRefresh: true,
      })
    );
  }
  await Promise.all(tasks);
}
