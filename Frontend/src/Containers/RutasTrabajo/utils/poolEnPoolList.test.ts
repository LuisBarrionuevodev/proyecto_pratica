import { beforeEach, describe, expect, it, vi } from "vitest";

import { listRutaPoolDia } from "../../../api/rutaPoolDiaApi";
import { fetchRutaPoolDiaEnPoolAll, POOL_EN_POOL_PAGE_SIZE } from "./poolEnPoolList";

vi.mock("../../../api/rutaPoolDiaApi", () => ({
  listRutaPoolDia: vi.fn(),
}));

const listMock = vi.mocked(listRutaPoolDia);

function poolRow(id: number) {
  return {
    pool_id: id,
    fecha: "2026-08-01",
    estado: "EN_POOL",
    iniciador_id: id,
    iniciador_ruta_id: id,
  };
}

describe("fetchRutaPoolDiaEnPoolAll", () => {
  beforeEach(() => {
    listMock.mockReset();
  });

  it("pagina hasta meta.total", async () => {
    const page1 = Array.from({ length: POOL_EN_POOL_PAGE_SIZE }, (_, i) => poolRow(i + 1));
    const page2 = [poolRow(POOL_EN_POOL_PAGE_SIZE + 1)];
    listMock
      .mockResolvedValueOnce({ items: page1, meta: { total: POOL_EN_POOL_PAGE_SIZE + 1, page: 1, per_page: POOL_EN_POOL_PAGE_SIZE } })
      .mockResolvedValueOnce({ items: page2, meta: { total: POOL_EN_POOL_PAGE_SIZE + 1, page: 2, per_page: POOL_EN_POOL_PAGE_SIZE } });

    const all = await fetchRutaPoolDiaEnPoolAll({ fecha: "2026-08-01", estado: "EN_POOL" });
    expect(all).toHaveLength(POOL_EN_POOL_PAGE_SIZE + 1);
    expect(listMock).toHaveBeenCalledTimes(2);
  });

  it("una sola página cuando total cabe en primera", async () => {
    listMock.mockResolvedValueOnce({
      items: [poolRow(1)],
      meta: { total: 1, page: 1, per_page: POOL_EN_POOL_PAGE_SIZE },
    });
    const all = await fetchRutaPoolDiaEnPoolAll({ fecha: "2026-08-01", estado: "EN_POOL" });
    expect(all).toHaveLength(1);
    expect(listMock).toHaveBeenCalledTimes(1);
  });
});
