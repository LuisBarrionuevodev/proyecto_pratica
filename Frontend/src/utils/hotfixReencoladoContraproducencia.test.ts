import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("HOTFIX reencolado contraproducencia — frontend", () => {
  it("Completar trabajo quita fila cerrada del listado local", () => {
    const src = read("src/Containers/CompletarTrabajos/views/CompletarTrabajosGridView.tsx");
    expect(src).toContain("removeRowByRutaItemId");
    expect(src).toMatch(/onSuccess[\s\S]*removeRowByRutaItemId/);
  });

  it("planificación recarga pendientes-contexto al cambiar ruta/distrito", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(src).toContain("getPlanificacionPendientesContexto");
    expect(src).toContain("distritoActivoId");
  });

  it("mapa operativo expone loadRealizados para refetch manual", () => {
    const src = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(src).toContain("loadRealizados");
    expect(src).not.toContain("loadPendientes");
  });
});
