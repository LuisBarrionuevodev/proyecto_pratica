import { describe, expect, it } from "vitest";

import {
  CORRECCION_CONTRIBUYENTE_HINT,
  CORRECCION_DOMICILIO_HINT,
  CORRECCION_SIN_CAMBIOS_HINT,
} from "./correccionEstablecimientoCopy";

describe("correccionEstablecimientoCopy", () => {
  it("no promete recálculo de coordenadas ni cambio de titular", () => {
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("mismo contribuyente");
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("no cambia el titular");
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("ni fusiona");
    expect(CORRECCION_DOMICILIO_HINT.toLowerCase()).toContain("no se recalculan coordenadas");
    expect(CORRECCION_SIN_CAMBIOS_HINT.toLowerCase()).toContain("no se desvincula");
  });
});
