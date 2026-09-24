import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { filtrarUrgentesVisibles } from "./planificacion/selectors/planificacionSelectors";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.6J — urgentes globales agregables", () => {
  it("M3 oculta urgentes en pool localmente sin refetch al mutar pool (7F.1)", () => {
    const src = read("Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(src).toContain("filtrarUrgentesVisibles(urgentesRaw, poolSet)");
    expect(src).toMatch(/\[rutaId,\s*loadUrgentes\]/);
    expect(src).not.toMatch(/poolIniciadorKey/);
  });

  it("M3 endpoint urgentes usa ruta borrador (planificacionApi)", () => {
    const api = read("Containers/RutasTrabajo/planificacion/api/planificacionApi.ts");
    expect(api).toContain("planificacion/urgentes");
    expect(api).toContain("getPlanificacionUrgentes");
  });

  it("filtrarUrgentesVisibles oculta filas ya en pool local", () => {
    const rows = [{ id: 1 }, { id: 2 }, { id: 3 }];
    const visibles = filtrarUrgentesVisibles(rows, new Set([2]));
    expect(visibles.map((r) => r.id)).toEqual([1, 3]);
  });

  it("filtrarUrgentesVisibles no duplica ni deja ítems del pool", () => {
    const rows = [{ id: 10 }, { id: 20 }];
    const pool = new Set([10, 20]);
    expect(filtrarUrgentesVisibles(rows, pool)).toEqual([]);
  });
});
