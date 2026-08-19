import type { OperativaComprobacionFiltroPayload } from "./buildOperativaComprobacionFiltroPayload";

export type ComprobacionPendientesTab = "expediente" | "oficio" | "reinspeccion";

export type RefreshComprobacionesPostOficioContext = {
  filters: OperativaComprobacionFiltroPayload | null;
  activeTab: ComprobacionPendientesTab | "recorrido";
  invalidatePendientesTabs: () => void;
  loadExpediente: (
    filters: OperativaComprobacionFiltroPayload | null,
    opts?: { silent?: boolean }
  ) => Promise<void>;
  loadOficio: (
    filters: OperativaComprobacionFiltroPayload | null,
    opts?: { silent?: boolean }
  ) => Promise<void>;
  loadRein: (
    filters: OperativaComprobacionFiltroPayload | null,
    opts?: { silent?: boolean }
  ) => Promise<void>;
};

/**
 * Refresca bandejas pendientes tras alta/edición/eliminación de oficio.
 * El tab activo (si es pendiente) muestra loader; el resto se sincroniza en silencio.
 */
export async function refreshComprobacionesPostOficio(
  ctx: RefreshComprobacionesPostOficioContext
): Promise<void> {
  ctx.invalidatePendientesTabs();
  const { filters, activeTab } = ctx;
  await Promise.all([
    ctx.loadExpediente(filters, { silent: activeTab !== "expediente" }),
    ctx.loadOficio(filters, { silent: activeTab !== "oficio" }),
    ctx.loadRein(filters, { silent: activeTab !== "reinspeccion" }),
  ]);
}
