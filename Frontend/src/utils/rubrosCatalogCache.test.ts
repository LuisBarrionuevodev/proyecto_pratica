import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRubrosCatalogo } from "../api/rubrosCatalogApi";
import {
  clearRubrosCatalogCache,
  fetchRubrosCatalogoCached,
  filterRubrosByQuery,
  mergeLegacyRubroNames,
  rubroItemsToNombres,
} from "./rubrosCatalogCache";

vi.mock("../api/rubrosCatalogApi", () => ({
  fetchRubrosCatalogo: vi.fn(),
}));

describe("rubrosCatalogCache STAB-8", () => {
  afterEach(() => {
    clearRubrosCatalogCache();
    vi.clearAllMocks();
  });

  it("cache evita requests repetidas", async () => {
    vi.mocked(fetchRubrosCatalogo).mockResolvedValue([
      { id: 1, nombre: "PANADERIA", activo: true },
    ]);
    const a = await fetchRubrosCatalogoCached();
    const b = await fetchRubrosCatalogoCached();
    expect(a).toEqual(b);
    expect(fetchRubrosCatalogo).toHaveBeenCalledTimes(1);
  });

  it("mergeLegacyRubroNames preserva valor histórico", () => {
    const out = mergeLegacyRubroNames(["ALMACEN"], "RUBRO_VIEJO");
    expect(out).toContain("ALMACEN");
    expect(out).toContain("RUBRO_VIEJO");
  });

  it("filterRubrosByQuery filtra localmente", () => {
    const items = [
      { id: 1, nombre: "PANADERIA" },
      { id: 2, nombre: "CARNICERIA" },
    ];
    expect(filterRubrosByQuery(items, "pan").map((i) => i.nombre)).toEqual(["PANADERIA"]);
  });

  it("rubroItemsToNombres ordena nombres", () => {
    expect(rubroItemsToNombres([{ id: 2, nombre: "Z" }, { id: 1, nombre: "A" }])).toEqual(["A", "Z"]);
  });
});
