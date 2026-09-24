import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { resolvePoolFechaConsulta } from "./hooks/useRutaPoolDiaBackend";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.6E — refresh pool tras quitar ítem de grupo", () => {
  const index = read("src/Containers/RutasTrabajo/index.tsx");
  const hook = read("src/Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts");
  const borrador = read("src/Containers/RutasTrabajo/hooks/useRutaTrabajoBorradorActions.ts");

  it("deleteItem dispara onAfterDeleteItem tras DELETE exitoso", () => {
    expect(borrador).toContain("onAfterDeleteItem");
    expect(borrador).toContain("deleteRutaItem");
    expect(borrador).toContain("onAfterDeleteItem()");
  });

  it("syncPoolTrasQuitarItem refresca borrador y pool con fecha de ruta", () => {
    expect(index).toContain("syncPoolTrasQuitarItem");
    expect(index).toContain("onAfterDeleteItem: syncPoolTrasQuitarItem");
    expect(index).toContain("refreshPool(ruta?.fecha");
    expect(index).toContain("refreshRutaBorrador({ showLoading: false })");
  });

  it("mapa operativo usa el mismo handler que asignación (con refresh pool)", () => {
    expect(index).toContain("onQuitarItem={vistaHistoricaReadOnly ? undefined : handleQuitarItem}");
    expect(index).not.toMatch(/onQuitarItem=\{vistaHistoricaReadOnly \? undefined : handleDeleteItem\}/);
  });

  it("refreshPool acepta fecha override para GET /ruta-pool-dia", () => {
    expect(hook).toContain("resolvePoolFechaConsulta");
    expect(hook).toContain('estado: "EN_POOL"');
    expect(hook).toContain("fechaOverride");
  });

  it("resolvePoolFechaConsulta prioriza fecha de ruta sobre fecha operativa del hook", () => {
    expect(resolvePoolFechaConsulta("2026-08-27", "2026-05-19")).toBe("2026-08-27");
    expect(resolvePoolFechaConsulta(null, "2026-08-27")).toBe("2026-08-27");
    expect(resolvePoolFechaConsulta("  ", null)).toBeNull();
  });
});
