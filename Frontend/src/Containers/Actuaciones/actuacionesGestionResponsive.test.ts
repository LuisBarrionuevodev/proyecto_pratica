import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-RESP-ACT.1 gestión responsive", () => {
  it("TableActuaciones alterna cards móvil y tabla sm+", () => {
    const table = read("src/Containers/Actuaciones/Components/TableActuaciones.tsx");
    expect(table).toContain("ActuacionesGestionMobileCardList");
    expect(table).toContain('breakpoints.up("sm")');
    expect(table).toContain("handleOpenRowDetalle");
    expect(table).toContain("MaterialReactTable");
  });

  it("cards reutilizan modal CRUD existente", () => {
    const cards = read("src/Containers/Actuaciones/Components/ActuacionesGestionMobileCardList.tsx");
    expect(cards).toContain("onOpenDetalle");
    expect(cards).toContain("Ver / editar");
  });
});
