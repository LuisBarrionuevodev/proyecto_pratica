import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("RutasTrabajo pool backend OPER-RUTA.6", () => {
  const index = read("src/Containers/RutasTrabajo/index.tsx");
  const hook = read("src/Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts");
  const panel = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");

  it("index usa hook backend en lugar de pool in-memory", () => {
    expect(index).toContain("useRutaPoolDiaBackend");
    expect(index).not.toContain("setPoolIniciadorIds");
    expect(index).toContain("agregarDesdePoolRuta");
  });

  it("hook consulta GET /ruta-pool-dia con estado EN_POOL", () => {
    expect(hook).toContain("listRutaPoolDia");
    expect(hook).toContain('estado: "EN_POOL"');
    expect(hook).toContain("deleteRutaPoolDia");
  });

  it("PoolDelDiaPanel renderiza filas backend con origen y estado", () => {
    expect(panel).toContain("IRutaPoolDiaRow");
    expect(panel).toContain("poolDiaOrigenLabel");
    expect(panel).toContain("pool-del-dia-list");
    expect(panel).toContain("pool-del-dia-row-");
    expect(panel).toContain("Sacar del pool");
    expect(panel).toContain("puedeSacarDelPoolPanel");
  });
});
