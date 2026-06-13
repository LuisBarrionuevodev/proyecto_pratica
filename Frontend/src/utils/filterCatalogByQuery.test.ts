import { describe, expect, it } from "vitest";

import type { CatalogItem } from "../api/gridApi";
import { filterCatalogItemsByQuery } from "./filterCatalogByQuery";

const ITEMS: CatalogItem[] = [
  { id: 1, nombre: "García, Juan", legajo: "101" },
  { id: 2, nombre: "López, María", legajo: "202" },
];

describe("filterCatalogItemsByQuery", () => {
  it("filtra por apellido en nombre", () => {
    const out = filterCatalogItemsByQuery(ITEMS, "garc");
    expect(out).toHaveLength(1);
    expect(out[0]?.id).toBe(1);
  });

  it("filtra por legajo", () => {
    const out = filterCatalogItemsByQuery(ITEMS, "202");
    expect(out).toHaveLength(1);
    expect(out[0]?.id).toBe(2);
  });

  it("sin query devuelve todo", () => {
    expect(filterCatalogItemsByQuery(ITEMS, "")).toHaveLength(2);
  });
});
