import { describe, expect, it } from "vitest";

import { formatEstadoOperativoPoolLabel } from "./formatEstadoOperativoPoolLabel";

describe("formatEstadoOperativoPoolLabel", () => {
  it("en_pool muestra En ruta con contexto", () => {
    expect(
      formatEstadoOperativoPoolLabel({
        estado_operativo_pool: "en_pool",
        pool_fecha: "2026-02-26",
        ruta_numero: 100,
        ruta_turno: "MANIANA",
      })
    ).toBe("En ruta (26/02/2026 - Ruta 100 - Turno Mañana)");
  });

  it("en_pool sin metadata usa fallback", () => {
    expect(formatEstadoOperativoPoolLabel({ estado_operativo_pool: "en_pool" })).toBe("En ruta");
  });

  it("en_ruta_borrador muestra En grupo asignado con contexto", () => {
    expect(
      formatEstadoOperativoPoolLabel({
        estado_operativo_pool: "en_ruta_borrador",
        ruta_fecha: "2026-08-24",
        ruta_numero: 100,
        ruta_turno: "TARDE",
      })
    ).toBe("En grupo asignado (24/08/2026 - Ruta 100 - Turno Tarde)");
  });

  it("pendiente mantiene label simple", () => {
    expect(formatEstadoOperativoPoolLabel({ estado_operativo_pool: "pendiente" })).toBe("Pendiente");
  });
});
