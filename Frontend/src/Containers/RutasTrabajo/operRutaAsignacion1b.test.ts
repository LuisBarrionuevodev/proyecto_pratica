import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.ASIGNACION-1B — Quitar OT en borrador", () => {
  const panel = read("Containers/RutasTrabajo/Components/PanelGruposRuta.tsx");
  const hook = read("Containers/RutasTrabajo/hooks/useRutaTrabajoBorradorActions.ts");
  const api = read("api/rutasTrabajoApi.ts");
  const index = read("Containers/RutasTrabajo/index.tsx");
  const view = read("Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");

  it("API — DELETE orden-trabajo", () => {
    expect(api).toContain("clearRutaItemOrdenTrabajo");
    expect(api).toMatch(/delete<IClearItemOtResponse>\([\s\S]*orden-trabajo/);
  });

  it("hook — clearOrdenTrabajo sin optimistic update", () => {
    expect(hook).toContain("clearRutaItemOrdenTrabajo");
    expect(hook).toContain("clearOrdenTrabajo");
    expect(hook).toMatch(/const resp = await clearRutaItemOrdenTrabajo[\s\S]*setItems/);
    expect(hook).not.toMatch(/clearOrdenTrabajo[\s\S]*setItems[\s\S]*await clearRutaItemOrdenTrabajo/);
  });

  it("panel — QUITAR OT visible solo con OT persistida y acción habilitada", () => {
    expect(panel).toContain("QUITAR OT");
    expect(panel).toMatch(/canQuitarOt=\{Boolean\(onQuitarOtItem\)\}/);
    expect(panel).toMatch(/canQuitarOt=\{canQuitarOt && item\.orden_trabajo_id != null\}/);
    expect(panel).toContain('dsVariant="danger"');
    expect(panel).toContain("ConfirmDialog");
    expect(panel).toMatch(/La OT quedará disponible para volver a utilizarse/);
  });

  it("panel — loading evita doble submit al quitar OT", () => {
    expect(panel).toContain("clearingOtItemId");
    expect(panel).toMatch(/disabled=\{savingThis \|\| clearingThis\}/);
    expect(panel).toMatch(/loading=\{clearingOtItemId != null\}/);
  });

  it("panel — éxito limpia draft y feedback", () => {
    expect(panel).toMatch(/feedback\.success\("Orden de trabajo quitada del ítem\."\)/);
    expect(panel).toMatch(/if \(ok\)[\s\S]*delete next\[item\.id\][\s\S]*setQuitarOtPending\(null\)/);
  });

  it("wiring — index y vista pasan onQuitarOtItem", () => {
    expect(index).toContain("clearOrdenTrabajo: handleClearOt");
    expect(index).toContain("onQuitarOtItem={handleClearOt}");
    expect(view).toContain("onQuitarOtItem");
    expect(view).toMatch(/onQuitarOtItem=\{onQuitarOtItem\}/);
  });

  it("read-only — sin onQuitarOtItem no muestra botón", () => {
    expect(panel).toMatch(/canQuitarOt=\{Boolean\(onQuitarOtItem\)\}/);
    expect(panel).toMatch(/\{canQuitarOt \? \(/);
  });

  it("PATCH guardar OT sigue intacto", () => {
    expect(hook).toContain("patchRutaItemOrdenTrabajo");
    expect(panel).toContain("Guardar OT");
  });

  it("assert_ruta_item_liberable_desde_grupo no tocado en frontend", () => {
    expect(panel).toContain("onQuitarItem");
    expect(panel).not.toContain("assert_ruta_item_liberable");
  });
});
