import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { filtrarUrgentesVisibles, sinPool } from "./planificacion/selectors/planificacionSelectors";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.7F.1 — sin refetch M4/M3 al mutar pool", () => {
  const controllerSrc = read("Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
  const poolHookSrc = read("Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts");

  it("M4 no refetch cuando cambia poolIniciadorIds (sin poolIniciadorKey en effect)", () => {
    expect(controllerSrc).not.toMatch(/poolIniciadorKey/);
    expect(controllerSrc).toMatch(/loadPendientesMapa/);
    expect(controllerSrc).toMatch(/\[loadPendientesMapa\]/);
    expect(controllerSrc).not.toMatch(/\[distritoActivoId,\s*rutaId,\s*poolIniciadorKey\]/);
  });

  it("M3 urgentes no refetch al mutar pool (solo rutaId en mount)", () => {
    expect(controllerSrc).toMatch(/loadUrgentes\(1,\s*25\)/);
    expect(controllerSrc).toMatch(/\[rutaId,\s*loadUrgentes\]/);
    expect(controllerSrc).not.toMatch(/\[loadUrgentes,\s*poolIniciadorKey\]/);
  });

  it("candidatos mapa ocultan pool localmente con sinPool", () => {
    expect(controllerSrc).toContain("sinPool(pendientesMapaRaw, poolSet)");
    const rows = [{ id: 1 }, { id: 2 }];
    expect(sinPool(rows, new Set([2])).map((r) => r.id)).toEqual([1]);
  });

  it("urgentes ocultan pool localmente sin refetch M3", () => {
    expect(controllerSrc).toContain("filtrarUrgentesVisibles(urgentesRaw, poolSet)");
    const visibles = filtrarUrgentesVisibles([{ id: 5 }, { id: 6 }], new Set([5]));
    expect(visibles.map((r) => r.id)).toEqual([6]);
  });

  it("agregar al pool refresca pool silent sin disparar M4/M3", () => {
    expect(poolHookSrc).toMatch(/refreshPool\(f,\s*\{\s*silent:\s*true\s*\}\)/);
    expect(controllerSrc).not.toContain("poolIniciadorKey");
  });

  it("quitar del pool refresca pool silent", () => {
    expect(poolHookSrc).toMatch(/deleteRutaPoolDia[\s\S]*refreshPool\(undefined,\s*\{\s*silent:\s*true\s*\}\)/);
  });

  it("expone refreshPendientesMapa para recarga manual de candidatos", () => {
    expect(controllerSrc).toContain("refreshPendientesMapa: () => loadPendientesMapa({ forceRefresh: true })");
  });

  it("quitar item / eliminar grupo no toca planificación M3/M4", () => {
    const index = read("Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("syncPoolTrasQuitarItem");
    expect(index).not.toContain("loadUrgentes");
    expect(index).not.toContain("getPlanificacionPendientesContexto");
  });
});
