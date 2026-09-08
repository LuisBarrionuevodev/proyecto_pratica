import type { OperativaPendientesTab } from "./operativaComprobacionBaseCache";
import type { OperativaComprobacionFiltroPayload } from "./buildOperativaComprobacionFiltroPayload";

export type ComprobacionPendientesTab = OperativaPendientesTab;

export type RefreshComprobacionesPostOficioContext = {
  filters: OperativaComprobacionFiltroPayload | null;
  activeTab: ComprobacionPendientesTab | "recorrido";
  invalidateOperativaBaseTabs: (tabs: ComprobacionPendientesTab[]) => void;
  loadExpediente: (
    filters: OperativaComprobacionFiltroPayload | null,
    opts?: { silent?: boolean; forceBaseRefresh?: boolean }
  ) => Promise<void>;
  loadOficio: (
    filters: OperativaComprobacionFiltroPayload | null,
    opts?: { silent?: boolean; forceBaseRefresh?: boolean }
  ) => Promise<void>;
  loadRein: (
    filters: OperativaComprobacionFiltroPayload | null,
    opts?: { silent?: boolean; forceBaseRefresh?: boolean }
  ) => Promise<void>;
};

/**
 * Tras mutación: invalida snapshots base afectados y recarga dataset base (sin filtros).
 * El tab activo muestra loader; el resto se sincroniza en silencio.
 */
export async function refreshComprobacionesPostOficio(
  ctx: RefreshComprobacionesPostOficioContext,
  invalidatedTabs: ComprobacionPendientesTab[]
): Promise<void> {
  if (invalidatedTabs.length === 0) return;
  ctx.invalidateOperativaBaseTabs(invalidatedTabs);
  const tasks: Promise<void>[] = [];
  if (invalidatedTabs.includes("expediente")) {
    tasks.push(ctx.loadExpediente(null, { silent: ctx.activeTab !== "expediente", forceBaseRefresh: true }));
  }
  if (invalidatedTabs.includes("oficio")) {
    tasks.push(ctx.loadOficio(null, { silent: ctx.activeTab !== "oficio", forceBaseRefresh: true }));
  }
  if (invalidatedTabs.includes("reinspeccion")) {
    tasks.push(ctx.loadRein(null, { silent: ctx.activeTab !== "reinspeccion", forceBaseRefresh: true }));
  }
  await Promise.all(tasks);
}

/** Tras registrar expediente de comprobación. */
export const MUTATION_INVALIDATE_EXPEDIENTE: ComprobacionPendientesTab[] = ["expediente", "oficio"];

/** Tras registrar oficio administrativo. */
export const MUTATION_INVALIDATE_OFICIO: ComprobacionPendientesTab[] = ["oficio", "reinspeccion"];

/** Tras cambios de pool/ruta que afectan elegibilidad de reinspección. */
export const MUTATION_INVALIDATE_REINSPECCION: ComprobacionPendientesTab[] = ["reinspeccion"];
