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

function sameIdSequence(a: readonly number[], b: readonly number[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

/**
 * Mantiene invariante selected ⊆ pool: filtra IDs que ya no están en el pool actual.
 * Retorna `prev` si no hubo cambios (evita setState redundante).
 */
export function reconcileSelectedIniciadorIds(
  selectedIds: readonly number[],
  currentPoolIniciadorIds: readonly number[]
): number[] {
  const valid = new Set(currentPoolIniciadorIds);
  const next = selectedIds.filter((id) => valid.has(id));
  return sameIdSequence(selectedIds, next) ? [...selectedIds] : next;
}
