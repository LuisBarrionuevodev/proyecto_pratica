import { describe, expect, it } from "vitest";

import { buildRutaContextoLine } from "./rutaResumenLabels";

describe("buildRutaContextoLine", () => {
  it("concatena estado, fecha, turno y sufijo opcional", () => {
    expect(
      buildRutaContextoLine({ estado_ruta: "BORRADOR", fecha: "2026-08-19", turno: "MANIANA" }, "En pool: 1")
    ).toBe("Borrador · 2026-08-19 · Mañana · En pool: 1");
  });

  it("omite partes vacías", () => {
    expect(buildRutaContextoLine({ fecha: "2026-08-19", turno: "TARDE" })).toBe("2026-08-19 · Tarde");
  });
});
