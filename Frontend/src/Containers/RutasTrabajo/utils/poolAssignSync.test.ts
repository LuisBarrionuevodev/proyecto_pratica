import { describe, expect, it } from "vitest";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";
import {
  filterPoolRowsDisponibles,
  prunePoolItemsByIds,
  resolvePoolIdsForIniciadores,
} from "./poolAssignSync";

function poolRow(poolId: number, iniciadorId: number): IRutaPoolDiaRow {
  return {
    pool_id: poolId,
    fecha: "2026-08-01",
    estado: "EN_POOL",
    iniciador_id: iniciadorId,
    iniciador_ruta_id: iniciadorId,
  } as IRutaPoolDiaRow;
}

function pendienteRow(id: number): IRutaIniciadorPendienteRow {
  return { id, tipo_iniciador: "RELEVAMIENTO" } as IRutaIniciadorPendienteRow;
}

describe("poolAssignSync", () => {
  it("resolvePoolIdsForIniciadores: todos resueltos", () => {
    const result = resolvePoolIdsForIniciadores([10, 20], { 10: 101, 20: 202 });
    expect(result.poolIds).toEqual([101, 202]);
    expect(result.missingIniciadorIds).toEqual([]);
  });

  it("resolvePoolIdsForIniciadores: detecta faltantes sin inferir", () => {
    const result = resolvePoolIdsForIniciadores([10, 20, 30], { 10: 101, 30: 303 });
    expect(result.poolIds).toEqual([101, 303]);
    expect(result.missingIniciadorIds).toEqual([20]);
  });

  it("prunePoolItemsByIds elimina solo pool_ids asignados", () => {
    const items = [poolRow(1, 10), poolRow(2, 20), poolRow(3, 30)];
    expect(prunePoolItemsByIds(items, [2]).map((r) => r.pool_id)).toEqual([1, 3]);
  });

  it("filterPoolRowsDisponibles excluye iniciadores ya asignados", () => {
    const rows = [pendienteRow(10), pendienteRow(20), pendienteRow(30)];
    const out = filterPoolRowsDisponibles(rows, new Set([20]));
    expect(out.map((r) => r.id)).toEqual([10, 30]);
  });
});
