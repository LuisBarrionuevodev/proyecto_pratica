import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  puedeAgregarAlPool,
  puedeAgregarARuta,
} from "../../utils/operRutaPoolAcciones";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("ActasComprobacion OPER-RUTA.5", () => {
  const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");

  it("Pendientes reinspección integra acciones pool", () => {
    expect(page).toContain("OperRutaPoolAccionesCell");
    expect(page).toContain("accion_rein");
    expect(cell).toContain("data-testid=\"oper-ruta-agregar-pool\"");
  });

  it("expediente y oficio no integran OperRutaPoolAccionesCell", () => {
    expect(page).not.toMatch(/columnsExpediente[\s\S]*OperRutaPoolAccionesCell/);
    expect(page).not.toMatch(/columnsOficio[\s\S]*OperRutaPoolAccionesCell/);
  });

  it("Recorrido no se modifica con acciones pool", () => {
    expect(page).not.toMatch(/tab === \"recorrido\"[\s\S]*OperRutaPoolAccionesCell/);
  });

  it("pendiente reinspección habilita pool", () => {
    expect(puedeAgregarAlPool({ iniciador_id: 12, estado_operativo_pool: "pendiente" })).toBe(true);
  });

  it("en_pool habilita agregar a ruta", () => {
    expect(puedeAgregarARuta({ iniciador_id: 12, estado_operativo_pool: "en_pool" })).toBe(true);
    expect(puedeAgregarAlPool({ iniciador_id: 12, estado_operativo_pool: "en_pool" })).toBe(false);
  });

  it("expediente/oficio sin iniciador planificable no habilita pool", () => {
    expect(puedeAgregarAlPool({ estado_operativo_pool: "no_elegible" })).toBe(false);
  });
});
