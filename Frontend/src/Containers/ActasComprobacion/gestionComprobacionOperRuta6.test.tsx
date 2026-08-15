import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { puedeAgregarARutaDeTrabajo } from "../../utils/operRutaPoolAcciones";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("ActasComprobacion OPER-RUTA.6", () => {
  const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");

  it("Pendientes reinspección integra botón único", () => {
    expect(page).toContain("OperRutaPoolAccionesCell");
    expect(page).toContain("accion_rein");
    expect(cell).toContain("Agregar a ruta de trabajo");
    expect(cell).not.toContain("oper-ruta-agregar-pool");
  });

  it("expediente y oficio no integran OperRutaPoolAccionesCell en columnas", () => {
    const expedienteBlock = page.split("const columnsExpediente")[1]?.split("const columnsOficio")[0] ?? "";
    const oficioBlock = page.split("const columnsOficio")[1]?.split("const columnsRein")[0] ?? "";
    expect(expedienteBlock).not.toContain("OperRutaPoolAccionesCell");
    expect(oficioBlock).not.toContain("OperRutaPoolAccionesCell");
  });

  it("Recorrido no integra acciones pool en columnas", () => {
    const recorridoBlock = page.split("const columnsRec")[1]?.split("export default")[0] ?? "";
    expect(recorridoBlock).not.toContain("OperRutaPoolAccionesCell");
  });

  it("pendiente reinspección habilita agregar a ruta de trabajo", () => {
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 12, estado_operativo_pool: "pendiente" })).toBe(true);
  });

  it("en_pool habilita agregar a ruta de trabajo", () => {
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 12, estado_operativo_pool: "en_pool" })).toBe(true);
  });
});
