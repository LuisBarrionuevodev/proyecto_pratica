import type { OperativaNotificacionFiltroPayload } from "./buildOperativaNotificacionFiltroPayload";
import type { OperativePlazoExpedienteSlice, PlazoOperativoSlice } from "../gestionNotificacionPlazo";

export type RefreshNotificacionesPostProrrogaContext = {
  filters: OperativaNotificacionFiltroPayload | null;
  activeSlice: PlazoOperativoSlice;
  invalidateOperativeSlices: () => void;
  loadPlazoSlice: (
    slice: OperativePlazoExpedienteSlice,
    force: boolean,
    filters: OperativaNotificacionFiltroPayload | null,
    opts?: { silent?: boolean }
  ) => Promise<void>;
  loadReinspeccion: (
    filters: OperativaNotificacionFiltroPayload | null,
    opts?: { silent?: boolean }
  ) => Promise<void>;
};

/**
 * Refresca slices operativos tras alta/edición/eliminación de prórroga.
 * El tab activo muestra loader; el resto se sincroniza en silencio.
 */
export async function refreshNotificacionesPostProrroga(
  ctx: RefreshNotificacionesPostProrrogaContext
): Promise<void> {
  ctx.invalidateOperativeSlices();
  const { filters, activeSlice } = ctx;
  await Promise.all([
    ctx.loadPlazoSlice("en_plazo", true, filters, { silent: activeSlice !== "en_plazo" }),
    ctx.loadPlazoSlice("por_vencer", true, filters, { silent: activeSlice !== "por_vencer" }),
    ctx.loadReinspeccion(filters, { silent: activeSlice !== "vencidas_o_hoy" }),
  ]);
}
