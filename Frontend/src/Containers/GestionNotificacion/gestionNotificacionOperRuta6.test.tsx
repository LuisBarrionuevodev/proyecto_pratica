import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { puedeAgregarARutaDeTrabajo } from "../../utils/operRutaPoolAcciones";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("GestionNotificacion OPER-RUTA.6", () => {
  const page = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");
  const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");

  it("Pendiente reinspección integra botón único Agregar a ruta de trabajo", () => {
    expect(page).toContain("OperRutaPoolAccionesCell");
    expect(page).toContain("columnsReinspeccionOperativa");
    expect(cell).toContain("Agregar a ruta de trabajo");
    expect(cell).not.toContain("Agregar al pool");
    expect(cell).not.toContain('data-testid="oper-ruta-agregar-pool"');
    expect(cell).not.toContain('data-testid="oper-ruta-agregar-ruta"');
    expect(cell).toContain('data-testid="oper-ruta-agregar-ruta-trabajo"');
  });

  it("modal muestra fecha y opción crear ruta", () => {
    expect(dialog).toContain("Fecha operativa");
    expect(dialog).toContain("oper-ruta-sin-ruta");
    expect(dialog).toContain("Crear ruta");
    expect(dialog).toContain("oper-ruta-solo-pool");
    expect(dialog).toContain("agregarDesdePoolRuta");
    expect(dialog).toContain("createRutaPoolDia");
  });

  it("en plazo / por vencer no integran acciones pool en columnas operativas", () => {
    const operativaBlock = page.split("const columnsOperativa")[1]?.split("const columnsHistorial")[0] ?? "";
    expect(operativaBlock).not.toContain("OperRutaPoolAccionesCell");
  });

  it("Historial no integra acciones pool", () => {
    const historialBlock = page.split("const columnsHistorial")[1]?.split("const columnsReinspeccionOperativa")[0] ?? "";
    expect(historialBlock).not.toContain("OperRutaPoolAccionesCell");
  });

  it("pendiente y en_pool habilitan agregar a ruta de trabajo", () => {
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 1, estado_operativo_pool: "pendiente" })).toBe(true);
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 1, estado_operativo_pool: "en_pool" })).toBe(true);
  });

  it("en_ruta_borrador no muestra acción", () => {
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 1, estado_operativo_pool: "en_ruta_borrador" })).toBe(false);
  });
});
