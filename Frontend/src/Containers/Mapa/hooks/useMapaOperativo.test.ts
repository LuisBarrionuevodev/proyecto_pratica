import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("useMapaOperativo — filtro tipo Realizados", () => {
  it("envía tipo operativo al API cuando hay valor", () => {
    const hook = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(hook).toContain("mapaRealizadosTipoQueryValue(p.tipo)");
    expect(hook).toContain("mapaRealizadosRubroQueryValue(p.rubroId");
    expect(hook).toContain("getMapOperativoRealizadosFC");
    expect(hook).not.toContain("definicion");
  });
});
