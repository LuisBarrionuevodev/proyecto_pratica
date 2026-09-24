import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";
import { puedeSacarDelPoolPanel } from "../../../../utils/operRutaPoolAcciones";
import { detalleOperativoTexto, tipoLabelOperativo } from "../../utils/iniciadorDetalleOperativo";

export type PlanificacionPoolStripItemEstado = "pool" | "grupo";

export type PlanificacionPoolStripItem = {
  key: string;
  iniciadorId: number;
  tipoLabel: string;
  titulo: string;
  detalle: string | null;
  distritoLabel: string;
  estado: PlanificacionPoolStripItemEstado;
  estadoLabel: string;
  grupoNombre: string | null;
  poolId: number | null;
  puedeQuitar: boolean;
};

export type PlanificacionPoolStripCounts = {
  enPool: number;
  enGrupo: number;
  total: number;
};

export type BuildPlanificacionPoolStripItemsInput = {
  poolItems: IRutaPoolDiaRow[];
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  poolRowsById?: Record<number, IRutaIniciadorPendienteRow>;
  candidatosByIniciadorId?: Record<number, IRutaIniciadorPendienteRow>;
};

function resolveIniciadorId(pool: IRutaPoolDiaRow): number | null {
  const id = Number(pool.iniciador_ruta_id ?? pool.iniciador_id);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function tituloDesdeFuentes(
  domicilio: string | null | undefined,
  fallback: IRutaIniciadorPendienteRow | undefined,
  operativo: IRutaPoolDiaRow | IRutaItemMin | IRutaIniciadorPendienteRow | undefined
): string {
  const dom = domicilio?.trim() || fallback?.domicilio_texto?.trim();
  if (dom) return dom;
  const det = detalleOperativoTexto(operativo ?? fallback);
  if (det) return det.length > 48 ? `${det.slice(0, 48)}…` : det;
  return "—";
}

function distritoLabelDesde(
  distritoNombre: string | null | undefined,
  distritoId: number | null | undefined,
  fallback?: IRutaIniciadorPendienteRow
): string {
  const nom = distritoNombre?.trim() || fallback?.distrito_nombre?.trim();
  if (nom) return nom;
  const id = distritoId ?? fallback?.distrito_id;
  if (id != null) return `Dto. ${id}`;
  return "—";
}

/**
 * Cards del strip superior: pool libre + ítems en grupo, deduplicados (prioridad grupo).
 */
export function buildPlanificacionPoolStripItems({
  poolItems,
  grupos,
  itemsActivos,
  poolRowsById = {},
  candidatosByIniciadorId = {},
}: BuildPlanificacionPoolStripItemsInput): PlanificacionPoolStripItem[] {
  const byId = new Map<number, PlanificacionPoolStripItem>();
  const grupoById = new Map(grupos.map((g) => [g.id, g]));
  const poolByIniciadorId = new Map<number, IRutaPoolDiaRow>();

  for (const pool of poolItems) {
    const iniId = resolveIniciadorId(pool);
    if (iniId == null) continue;
    poolByIniciadorId.set(iniId, pool);
    if (pool.ruta_item_id != null) continue;

    const fallback = poolRowsById[iniId] ?? candidatosByIniciadorId[iniId];
    byId.set(iniId, {
      key: `pool-${pool.pool_id}`,
      iniciadorId: iniId,
      tipoLabel: tipoLabelOperativo(pool),
      titulo: tituloDesdeFuentes(pool.domicilio_texto, fallback, pool),
      detalle: detalleOperativoTexto(pool) ?? detalleOperativoTexto(fallback),
      distritoLabel: distritoLabelDesde(pool.distrito_nombre, pool.distrito_id, fallback),
      estado: "pool",
      estadoLabel: "En pool",
      grupoNombre: null,
      poolId: pool.pool_id,
      puedeQuitar: puedeSacarDelPoolPanel(pool),
    });
  }

  for (const item of itemsActivos) {
    if (item.deleted_at) continue;
    const iniId = item.iniciador_ruta_id;
    if (!iniId) continue;

    const pool = poolByIniciadorId.get(iniId);
    const fallback = poolRowsById[iniId] ?? candidatosByIniciadorId[iniId];
    const grupo = grupoById.get(item.ruta_grupo_id);
    const operativo = pool ?? item;

    byId.set(iniId, {
      key: `grupo-${item.id}`,
      iniciadorId: iniId,
      tipoLabel: tipoLabelOperativo(operativo),
      titulo: tituloDesdeFuentes(item.domicilio_texto ?? pool?.domicilio_texto, fallback, operativo),
      detalle: detalleOperativoTexto(operativo) ?? detalleOperativoTexto(fallback),
      distritoLabel: distritoLabelDesde(
        item.distrito_nombre ?? pool?.distrito_nombre,
        item.distrito_id ?? pool?.distrito_id,
        fallback
      ),
      estado: "grupo",
      estadoLabel: "En grupo",
      grupoNombre: grupo?.nombre ?? null,
      poolId: pool?.pool_id ?? null,
      puedeQuitar: false,
    });
  }

  return Array.from(byId.values());
}

export function countPlanificacionPoolStripItems(items: PlanificacionPoolStripItem[]): PlanificacionPoolStripCounts {
  let enPool = 0;
  let enGrupo = 0;
  for (const it of items) {
    if (it.estado === "pool") enPool += 1;
    else enGrupo += 1;
  }
  return { enPool, enGrupo, total: items.length };
}
