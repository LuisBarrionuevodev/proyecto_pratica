import { describe, expect, it } from "vitest";

import { ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION } from "./institutionalCopy";

describe("ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION V1.1-OT-EXPORT.1", () => {
  it("conserva el número de resolución vigente", () => {
    expect(ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION).toContain("3679/DCH/26");
    expect(ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION).toContain("Resolución N.º 3679/DCH/26");
  });

  it("describe autorización de agentes individualizados para inspección del domicilio", () => {
    expect(ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION).toMatch(/agentes mencionados/i);
    expect(ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION).toMatch(/inspección del domicilio asignado/i);
    expect(ORDEN_TRABAJO_DEPARTAMENTAL_LEYENDA_CAPACITACION).not.toMatch(
      /INSPECTORES CAPACITADOS EN PROCEDIMIENTOS DE FISCALIZACIÓN/i
    );
  });
});
