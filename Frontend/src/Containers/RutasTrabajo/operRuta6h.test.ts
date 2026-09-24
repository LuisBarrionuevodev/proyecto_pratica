import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.6H — pool acotado por ruta_trabajo_id", () => {
  const hook = read("src/Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts");
  const index = read("src/Containers/RutasTrabajo/index.tsx");
  const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");
  const api = read("src/api/rutaPoolDiaApi.ts");

  it("API soporta ruta_trabajo_id en listado", () => {
    expect(api).toContain("ruta_trabajo_id?: number");
  });

  it("useRutaPoolDiaBackend filtra GET por ruta_trabajo_id", () => {
    expect(hook).toContain("rutaTrabajoId");
    expect(hook).toContain("ruta_trabajo_id: rutaIdOperativa");
    expect(hook).toContain("rutaIdOperativa");
  });

  it("index pasa rutaTrabajoId al hook", () => {
    expect(index).toContain("rutaTrabajoId: rutaId");
  });

  it("agregarAlPool crea pool con ruta_trabajo_id de la ruta abierta", () => {
    expect(hook).toContain("ruta_trabajo_id: rutaIdOperativa");
  });

  it("quitarDelPool opera por pool_id", () => {
    expect(hook).toContain("deleteRutaPoolDia(poolId)");
    expect(hook).not.toMatch(/deleteRutaPoolDia\(.*iniciador/i);
  });

  it("resolverPoolId lista pool filtrado por ruta seleccionada", () => {
    expect(dialog).toContain("ruta_trabajo_id: selectedRutaId");
  });

  it("cambio de ruta refresca pool con nuevo rutaTrabajoId", () => {
    expect(hook).toMatch(/\[fechaOperativa,\s*rutaIdOperativa,\s*onError\]/);
  });
});
