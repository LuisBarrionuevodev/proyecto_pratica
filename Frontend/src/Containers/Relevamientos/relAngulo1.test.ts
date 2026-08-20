import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { applyEstablecimientoCamposToPayload, buildNumeroTipoDraftPatch } from "./utils/relevamientoCamposForm";
import { relevamientoAnguloEsquinaDisplay } from "./utils/relevamientoCrudDisplay";
import { normalizeRelevamientoRowForApi } from "./utils/submitRelevamientoRow";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("REL-ANGULO.1 — angulo_esquina relevamiento ESQUINA", () => {
  it("alta ESQUINA: payload incluye angulo_esquina normalizado", () => {
    const out = normalizeRelevamientoRowForApi({
      id: 1,
      fecha: "2026-05-10",
      inspector: "X",
      calle: "Maipú",
      numero: "y Salta",
      numero_tipo: "ESQUINA",
      rubro: "Carnicería",
      angulo_esquina: "ne",
    } as any);
    expect(out.angulo_esquina).toBe("NE");
  });

  it("NUMERO/OTRO: payload limpia angulo_esquina", () => {
    const out = normalizeRelevamientoRowForApi({
      id: 1,
      fecha: "2026-05-10",
      inspector: "X",
      calle: "Maipú",
      numero: "100",
      numero_tipo: "NUMERO",
      rubro: "Carnicería",
      angulo_esquina: "NE",
    } as any);
    expect(out.angulo_esquina).toBeNull();
  });

  it("cambio ESQUINA → NUMERO limpia ángulo en draft", () => {
    const patch = buildNumeroTipoDraftPatch("NUMERO", {
      numero_tipo: "ESQUINA",
      numero: "Belgrano y Mitre",
      angulo_esquina: "SO",
    } as any);
    expect(patch.angulo_esquina).toBeNull();
  });

  it("tabla muestra ángulo en ESQUINA y — en NUMERO", () => {
    expect(
      relevamientoAnguloEsquinaDisplay({
        numero_tipo: "ESQUINA",
        numero: "y Norte",
        angulo_esquina: "NE",
      } as any)
    ).toBe("NE");
    expect(
      relevamientoAnguloEsquinaDisplay({
        numero_tipo: "NUMERO",
        numero: "100",
        angulo_esquina: "NE",
      } as any)
    ).toBeNull();
  });

  it("applyEstablecimientoCamposToPayload conserva ángulo en ESQUINA", () => {
    const row = applyEstablecimientoCamposToPayload({
      id: 1,
      fecha: null,
      inspector: null,
      calle: "X",
      numero: "y Y",
      numero_tipo: "ESQUINA",
      rubro: null,
      angulo_esquina: "so",
    } as any);
    expect(row.angulo_esquina).toBe("SO");
  });

  it("TableRelevamientos incluye columna Ángulo", () => {
    const src = read("Containers/Relevamientos/Components/TableRelevamientos.tsx");
    expect(src).toContain('accessorKey: "angulo_esquina"');
    expect(src).toContain('header: "Ángulo"');
    expect(src).toContain("relevamientoAnguloEsquinaDisplay");
  });
});
