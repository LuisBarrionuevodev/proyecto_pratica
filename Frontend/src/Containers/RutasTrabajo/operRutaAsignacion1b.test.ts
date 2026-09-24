import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.ASIGNACION-1B — OT-AUTO sin asignación manual", () => {
  const panel = read("Containers/RutasTrabajo/Components/PanelGruposRuta.tsx");
  const hook = read("Containers/RutasTrabajo/hooks/useRutaTrabajoBorradorActions.ts");
  const index = read("Containers/RutasTrabajo/index.tsx");
  const view = read("Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");

  it("panel — sin UI de OT manual en asignación", () => {
    expect(panel).not.toContain("Guardar OT");
    expect(panel).not.toContain("QUITAR OT");
    expect(panel).not.toMatch(/orden_trabajo_id/);
  });

  it("index — sin wiring de quitar/guardar OT en asignación", () => {
    expect(index).not.toContain("onQuitarOtItem");
    expect(index).not.toContain("handleClearOt");
    expect(index).not.toContain("saveOtItem");
  });

  it("vista planificación — sin props OT manual", () => {
    expect(view).not.toContain("onQuitarOtItem");
    expect(view).not.toContain("onSaveOtItem");
  });

  it("hook — mutaciones de borrador sin OT en flujo activo", () => {
    expect(hook).toContain("moveItem");
    expect(hook).toContain("deleteItem");
  });

  it("panel — mover/quitar ítem siguen disponibles", () => {
    expect(panel).toContain("onQuitarItem");
    expect(panel).not.toContain("assert_ruta_item_liberable");
  });
});
