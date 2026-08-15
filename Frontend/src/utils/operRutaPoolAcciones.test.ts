import { describe, expect, it } from "vitest";

import {
  puedeAgregarAlPool,
  puedeAgregarARuta,
  mostrarAccionesOperRutaPool,
} from "../../utils/operRutaPoolAcciones";

describe("operRutaPoolAcciones", () => {
  const base = { iniciador_id: 301 };

  it("pendiente habilita pool y ruta", () => {
    const row = { ...base, estado_operativo_pool: "pendiente" };
    expect(puedeAgregarAlPool(row)).toBe(true);
    expect(puedeAgregarARuta(row)).toBe(true);
    expect(mostrarAccionesOperRutaPool(row)).toBe(true);
  });

  it("en_pool solo habilita agregar a ruta", () => {
    const row = { ...base, estado_operativo_pool: "en_pool" };
    expect(puedeAgregarAlPool(row)).toBe(false);
    expect(puedeAgregarARuta(row)).toBe(true);
  });

  it("en_ruta_borrador no muestra acciones", () => {
    const row = { ...base, estado_operativo_pool: "en_ruta_borrador" };
    expect(mostrarAccionesOperRutaPool(row)).toBe(false);
  });

  it("no_elegible sin iniciador no muestra acciones", () => {
    expect(mostrarAccionesOperRutaPool({ estado_operativo_pool: "no_elegible" })).toBe(false);
    expect(mostrarAccionesOperRutaPool({ iniciador_id: null, estado_operativo_pool: "pendiente" })).toBe(
      false
    );
  });
});
