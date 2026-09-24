import { describe, expect, it } from "vitest";

import {
  estaBloqueadoParaGestionDocumental,
  puedeAgregarARutaDeTrabajo,
  puedeSacarDelPool,
  puedeSacarDeRutaPool,
  puedeSacarDelPoolPanel,
  mostrarAccionesOperRutaPool,
} from "./operRutaPoolAcciones";

describe("operRutaPoolAcciones OPER-RUTA.6B", () => {
  const base = { iniciador_id: 301 };

  it("pendiente habilita agregar a ruta de trabajo", () => {
    expect(puedeAgregarARutaDeTrabajo({ ...base, estado_operativo_pool: "pendiente" })).toBe(true);
  });

  it("en_pool habilita agregar y sacar del pool", () => {
    const row = { ...base, estado_operativo_pool: "en_pool", pool_id: 9 };
    expect(puedeAgregarARutaDeTrabajo(row)).toBe(true);
    expect(puedeSacarDelPool(row)).toBe(true);
  });

  it("en_ruta_borrador bloquea gestión y permite sacar sin OT", () => {
    const row = {
      ...base,
      estado_operativo_pool: "en_ruta_borrador",
      pool_id: 9,
      ruta_status: "BORRADOR",
      tiene_orden_trabajo: false,
    };
    expect(estaBloqueadoParaGestionDocumental(row)).toBe(true);
    expect(puedeSacarDeRutaPool(row)).toBe(true);
    expect(puedeAgregarARutaDeTrabajo(row)).toBe(false);
  });

  it("en_ruta_borrador con OT no permite sacar", () => {
    expect(
      puedeSacarDeRutaPool({
        ...base,
        estado_operativo_pool: "en_ruta_borrador",
        pool_id: 9,
        ruta_status: "BORRADOR",
        tiene_orden_trabajo: true,
      })
    ).toBe(false);
  });

  it("pool panel solo EN_POOL sin ruta_item", () => {
    expect(puedeSacarDelPoolPanel({ estado: "EN_POOL", ruta_item_id: null })).toBe(true);
    expect(puedeSacarDelPoolPanel({ estado: "EN_POOL", ruta_item_id: 12 })).toBe(false);
    expect(puedeSacarDelPoolPanel({ estado: "ASIGNADO_A_RUTA" })).toBe(false);
  });

  it("mostrar acciones combina agregar y liberar", () => {
    expect(mostrarAccionesOperRutaPool({ ...base, estado_operativo_pool: "pendiente" })).toBe(true);
    expect(mostrarAccionesOperRutaPool({ ...base, estado_operativo_pool: "en_pool", pool_id: 1 })).toBe(true);
    expect(mostrarAccionesOperRutaPool({ ...base, estado_operativo_pool: "resuelto" })).toBe(false);
  });
});
