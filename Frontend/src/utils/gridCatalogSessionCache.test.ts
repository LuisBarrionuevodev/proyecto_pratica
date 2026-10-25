import { afterEach, describe, expect, it, vi } from "vitest";
import {
  clearGridCatalogSessionCaches,
  fetchGridCatalogSessionCached,
} from "./gridCatalogSessionCache";

describe("gridCatalogSessionCache PERF.3", () => {
  afterEach(() => {
    clearGridCatalogSessionCaches();
  });

  it("dos consumidores simultáneos del mismo catálogo: una request", async () => {
    const load = vi.fn().mockResolvedValue({ items: [{ nombre: "Inspector A" }] });
    const [a, b] = await Promise.all([
      fetchGridCatalogSessionCached("/grid/catalogs/inspectores", load),
      fetchGridCatalogSessionCached("/grid/catalogs/inspectores", load),
    ]);
    expect(a.items).toHaveLength(1);
    expect(b.items).toHaveLength(1);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("tras clear vuelve a cargar", async () => {
    const load = vi
      .fn()
      .mockResolvedValueOnce({ items: [{ nombre: "A" }] })
      .mockResolvedValueOnce({ items: [{ nombre: "B" }] });

    await fetchGridCatalogSessionCached("/grid/catalogs/motivos", load);
    clearGridCatalogSessionCaches();
    const second = await fetchGridCatalogSessionCached("/grid/catalogs/motivos", load);
    expect(second.items?.[0]?.nombre).toBe("B");
    expect(load).toHaveBeenCalledTimes(2);
  });
});
