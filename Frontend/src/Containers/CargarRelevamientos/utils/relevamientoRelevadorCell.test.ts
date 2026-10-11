import { describe, expect, it } from "vitest";
import {
  parseRelevadorCellValue,
  resolveRelevadorIdsFromNombres,
} from "./relevamientoRelevadorCell";
import { syncRelevadorIdsOnRow } from "./relevamientoDraftSessionStorage";

const catalog = [
  { id: 42, nombre: "Esquivel, Fabian" },
  { id: 7, nombre: "Medina, Oscar" },
];

describe("relevador celda — formato catálogo Apellido, Nombre", () => {
  it("parseRelevadorCellValue no parte por coma (un solo relevador)", () => {
    expect(parseRelevadorCellValue("Esquivel, Fabian")).toEqual(["Esquivel, Fabian"]);
  });

  it("resolveRelevadorIdsFromNombres acepta etiqueta catálogo y legacy Nombre Apellido", () => {
    expect(resolveRelevadorIdsFromNombres(["Esquivel, Fabian"], catalog)).toEqual([42]);
    expect(resolveRelevadorIdsFromNombres(["Fabian Esquivel"], catalog)).toEqual([42]);
  });

  it("syncRelevadorIdsOnRow conserva la etiqueta del catálogo sin reescribirla", () => {
    const row = {
      Relevador: "Esquivel, Fabian",
      Calle: "Test",
    } as Record<string, unknown>;
    const synced = syncRelevadorIdsOnRow(row as never, catalog);
    expect(synced.Relevador).toBe("Esquivel, Fabian");
    expect((synced as { _relevadorIds?: number[] })._relevadorIds).toEqual([42]);
  });
});
