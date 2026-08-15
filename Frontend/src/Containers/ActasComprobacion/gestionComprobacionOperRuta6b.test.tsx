import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("ActasComprobacion OPER-RUTA.6B", () => {
  const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");
  const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");

  it("bloquea Gestionar oficio cuando está en pool/ruta", () => {
    expect(page).toContain("estaBloqueadoParaGestionDocumental");
    expect(page).toContain("MENSAJE_BLOQUEO_GESTION_POOL_RUTA");
  });

  it("muestra Sacar del pool y liberar", () => {
    expect(cell).toContain("Sacar del pool");
    expect(cell).toContain("Sacar de ruta/pool");
  });

  it("modal permite solo pool sin grupo obligatorio", () => {
    expect(dialog).toContain("Agregar solo al pool del día");
  });
});
