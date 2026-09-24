import { afterEach, describe, expect, it, vi } from "vitest";

import { searchActuaciones } from "./actuacionesSearchApi";
import { apiClient } from "./apiClient";

vi.mock("./apiClient", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

describe("actuacionesSearchApi", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("searchActuaciones pasa q y limit al endpoint", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [{ id: 1, label: "OT 1" }] },
    });
    const items = await searchActuaciones("san martin", 15);
    expect(apiClient.get).toHaveBeenCalledWith("/actuaciones/search", {
      params: { q: "san martin", limit: 15 },
      signal: undefined,
    });
    expect(items).toHaveLength(1);
  });
});
