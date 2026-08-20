import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.6I — mapa candidatos + pool quitar", () => {
  it("M4 oculta candidatos en pool localmente sin refetch (OPER-RUTA.7F.1)", () => {
    const src = read("Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(src).toContain("sinPool(pendientesMapaRaw, poolSet)");
    expect(src).toContain("loadPendientesMapa");
    expect(src).not.toMatch(/poolIniciadorKey/);
  });

  it("planificación M4 usa solo agregables vía backend (pendientes-contexto)", () => {
    const planif = read("Containers/RutasTrabajo/planificacion/api/planificacionApi.ts");
    expect(planif).toContain("pendientes-contexto");
  });

  it("agregar al pool envía ruta_trabajo_id y evita doble click", () => {
    const hook = read("Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts");
    expect(hook).toContain("ruta_trabajo_id: rutaIdOperativa");
    expect(hook).toContain("agregandoRef");
    expect(hook).toContain("Agregando");
  });

  it("mapa muestra busy al agregar desde geocodificación", () => {
    const card = read(
      "Containers/RutasTrabajo/planificacion/components/PlanificacionMapaGeopuntoOperativaCard.tsx"
    );
    expect(card).toContain("agregando");
    expect(card).toContain("Agregando…");
  });

  it("quitar item refresca pool con syncPoolTrasQuitarItem", () => {
    const index = read("Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("syncPoolTrasQuitarItem");
    expect(index).toContain("refreshPool(ruta?.fecha, { silent: true })");
  });

  it("eliminar grupo refresca borrador y pool", () => {
    const index = read("Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("refreshRutaBorrador({ showLoading: false })");
    expect(index).toMatch(/handleDeleteGrupo[\s\S]*refreshPool\(ruta\?\.fecha/);
  });
});
