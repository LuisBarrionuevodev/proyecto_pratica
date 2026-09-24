import { describe, expect, it } from "vitest";

import {
  buildClientPaginationSummary,
  DEFAULT_BANDEJA_CLIENT_PAGE_SIZE,
  resetClientPaginationPageIndex,
} from "./buildClientPaginationSummary";

describe("buildClientPaginationSummary", () => {
  it("página 1 de 4 con 37 filas y pageSize 10", () => {
    const s = buildClientPaginationSummary({ pageIndex: 0, pageSize: 10, totalRows: 37 });
    expect(s.currentPage).toBe(1);
    expect(s.totalPages).toBe(4);
    expect(s.visibleRows).toBe(10);
    expect(s.totalRows).toBe(37);
  });

  it("página 2 de 4 muestra 10 visibles", () => {
    const s = buildClientPaginationSummary({ pageIndex: 1, pageSize: 10, totalRows: 37 });
    expect(s.currentPage).toBe(2);
    expect(s.totalPages).toBe(4);
    expect(s.visibleRows).toBe(10);
  });

  it("última página muestra resto (7 de 37)", () => {
    const s = buildClientPaginationSummary({ pageIndex: 3, pageSize: 10, totalRows: 37 });
    expect(s.currentPage).toBe(4);
    expect(s.visibleRows).toBe(7);
  });

  it("sin filas devuelve ceros visibles", () => {
    const s = buildClientPaginationSummary({ pageIndex: 0, pageSize: 10, totalRows: 0 });
    expect(s.visibleRows).toBe(0);
    expect(s.totalRows).toBe(0);
  });

  it("resetClientPaginationPageIndex conserva pageSize", () => {
    expect(resetClientPaginationPageIndex({ pageIndex: 3, pageSize: 25 })).toEqual({
      pageIndex: 0,
      pageSize: 25,
    });
  });

  it("default page size es 10", () => {
    expect(DEFAULT_BANDEJA_CLIENT_PAGE_SIZE).toBe(10);
  });
});
