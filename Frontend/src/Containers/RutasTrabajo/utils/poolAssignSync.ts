import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";

export type ResolvePoolIdsResult = {
  poolIds: number[];
  missingIniciadorIds: number[];
};

/**
 * Resuelve pool_id por iniciador para asignación desde Pool.
 * No infiere ni mezcla orígenes: cada iniciador debe tener poolId explícito.
 */
export function resolvePoolIdsForIniciadores(
  iniciadorIds: readonly number[],
  poolIdByIniciadorId: Readonly<Record<number, number>>
): ResolvePoolIdsResult {
  const poolIds: number[] = [];
  const missingIniciadorIds: number[] = [];

  for (const iniciadorId of iniciadorIds) {
    const poolId = poolIdByIniciadorId[iniciadorId];
    if (poolId != null && Number.isFinite(poolId)) {
      poolIds.push(poolId);
    } else {
      missingIniciadorIds.push(iniciadorId);
    }
  }

  return { poolIds, missingIniciadorIds };
}

/**
 * Elimina del snapshot local las filas pool asignadas (por pool_id).
 */
export function prunePoolItemsByIds(
  items: readonly IRutaPoolDiaRow[],
  assignedPoolIds: readonly number[]
): IRutaPoolDiaRow[] {
  if (assignedPoolIds.length === 0) return [...items];
  const remove = new Set(assignedPoolIds);
  return items.filter((row) => !remove.has(row.pool_id));
}

/**
 * Filas de pool visibles en Asignación: excluye iniciadores ya en un grupo de la ruta.
 */
export function filterPoolRowsDisponibles(
  rows: readonly IRutaIniciadorPendienteRow[],
  assignedIniciadorIds: ReadonlySet<number>
): IRutaIniciadorPendienteRow[] {
  if (assignedIniciadorIds.size === 0) return [...rows];
  return rows.filter((row) => !assignedIniciadorIds.has(row.id));
}
