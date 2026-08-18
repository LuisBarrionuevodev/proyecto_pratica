import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { buildClientPaginationSummary } from "../../utils/buildClientPaginationSummary";

const pagePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "GestionNotificacionPage.tsx"
);

describe("FILTROS-4 Notificaciones Historial paginación UI", () => {
  const src = () => readFileSync(pagePath, "utf8");

  it("no muestra Página: 1 hardcodeado", () => {
    expect(src()).not.toMatch(/<strong>Página:<\/strong>\s*1/);
    expect(src()).not.toContain("<strong>Página:</strong> 1");
  });

  it("usa paginación controlada y helper de resumen", () => {
    const s = src();
    expect(s).toContain("historialPagination");
    expect(s).toContain("setHistorialPagination");
    expect(s).toContain("buildClientPaginationSummary");
    expect(s).toContain("BandejaTableSummary");
    expect(s).toContain("onPaginationChange={setHistorialPagination}");
    expect(s).toContain("resetClientPaginationPageIndex");
  });

  it("resetea página al filtrar y limpiar", () => {
    const s = src();
    expect(s).toContain("setHistorialPagination((prev) => resetClientPaginationPageIndex(prev))");
  });

  it("con 37 filas y pageSize 10 muestra Página 1 de 4", () => {
    const s = buildClientPaginationSummary({ pageIndex: 0, pageSize: 10, totalRows: 37 });
    expect(s.currentPage).toBe(1);
    expect(s.totalPages).toBe(4);
    expect(s.visibleRows).toBe(10);
  });

  it("en página 2 muestra Página 2 de 4", () => {
    const s = buildClientPaginationSummary({ pageIndex: 1, pageSize: 10, totalRows: 37 });
    expect(s.currentPage).toBe(2);
    expect(s.totalPages).toBe(4);
  });

  it("en página 4 muestra Mostrando 7 de 37", () => {
    const s = buildClientPaginationSummary({ pageIndex: 3, pageSize: 10, totalRows: 37 });
    expect(s.visibleRows).toBe(7);
    expect(s.totalRows).toBe(37);
  });
});
