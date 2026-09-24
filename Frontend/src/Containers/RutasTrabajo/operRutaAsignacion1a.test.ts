import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { filterPoolRowsDisponibles, prunePoolItemsByIds } from "./utils/poolAssignSync";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.ASIGNACION-1A — Pool sale del listado al asignar", () => {
  const index = read("Containers/RutasTrabajo/index.tsx");
  const hook = read("Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts");
  const tabla = read("Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
  const strip = read("Containers/RutasTrabajo/planificacion/utils/buildPlanificacionPoolStripItems.ts");

  it("caso primary — solo agregar-desde-pool, sin fallback items:assign", () => {
    expect(index).toContain("agregarDesdePoolRuta");
    expect(index).not.toContain("assignRutaItems");
    expect(index).not.toContain("items:assign");
    expect(index).toContain("resolvePoolIdsForIniciadores");
    expect(index).toMatch(/missingIniciadorIds\.length > 0[\s\S]*refreshPool/);
  });

  it("caso primary — prune local inmediato + refreshPool silent", () => {
    expect(index).toContain("prunePoolEntriesByIds(poolIds)");
    expect(index).toMatch(/prunePoolEntriesByIds\(poolIds\)[\s\S]*refreshPool\(ruta\?\.fecha, \{ silent: true \}\)/);
  });

  it("contador y tabla usan pool disponible excluyendo asignados", () => {
    expect(index).toContain("poolRowsDisponibles");
    expect(index).toContain("filterPoolRowsDisponibles");
    expect(index).toMatch(/totalEnPool=\{poolRowsDisponibles\.length\}/);
    expect(tabla).toContain("rowsDisponibles");
    expect(tabla).toMatch(/data: rowsDisponibles/);
  });

  it("refreshPool con seq guard y paginación completa", () => {
    expect(hook).toContain("refreshPoolReqSeq");
    expect(hook).toMatch(/if \(seq !== refreshPoolReqSeq\.current\) return/);
    expect(hook).toContain("fetchRutaPoolDiaEnPoolAll");
    expect(hook).not.toMatch(/per_page: 100,\s*\n\s*\}\)/);
  });

  it("strip sigue deduplicando grupo sobre pool", () => {
    expect(strip).toContain('if (pool.ruta_item_id != null) continue');
    expect(strip).toContain('estado: "grupo"');
  });

  it("prune y filtro defensivo — unidad", () => {
    const pruned = prunePoolItemsByIds(
      [{ pool_id: 1, iniciador_id: 10 } as never, { pool_id: 2, iniciador_id: 20 } as never],
      [1]
    );
    expect(pruned).toHaveLength(1);
    expect(pruned[0].pool_id).toBe(2);

    const visibles = filterPoolRowsDisponibles(
      [{ id: 10 } as never, { id: 20 } as never],
      new Set([10])
    );
    expect(visibles.map((r) => r.id)).toEqual([20]);
  });
});
