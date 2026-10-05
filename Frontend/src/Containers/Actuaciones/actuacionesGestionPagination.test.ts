import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("Actuaciones gestión paginación móvil", () => {
  it("mobile usa listadoServidor del mismo TableActuaciones", () => {
    const table = read("src/Containers/Actuaciones/Components/TableActuaciones.tsx");
    expect(table).toContain("listadoServidor={listadoServidor}");
    expect(table).toContain("ActuacionesGestionMobileCardList");
  });

  it("paginación compartida expone anterior/siguiente y totales", () => {
    const pag = read("src/Containers/Actuaciones/Components/ActuacionesGestionListPagination.tsx");
    expect(pag).toContain("actuaciones-gestion-pagination");
    expect(pag).toContain("Anterior");
    expect(pag).toContain("Siguiente");
    expect(pag).toContain("Página");
    expect(pag).toContain("onPageChange");
  });

  it("filtro nuevo fuerza página 1", () => {
    const container = read("src/Containers/Actuaciones/ActuacionesContainer.tsx");
    expect(container).toContain("handleFiltrarTodos");
    expect(container).toMatch(/page:\s*1/);
  });

  it("mobile muestra paginación siempre con listado servidor", () => {
    const cards = read("src/Containers/Actuaciones/Components/ActuacionesGestionMobileCardList.tsx");
    expect(cards).toContain("ActuacionesGestionListPagination");
    expect(cards).not.toContain("total > pageSize");
  });
});
