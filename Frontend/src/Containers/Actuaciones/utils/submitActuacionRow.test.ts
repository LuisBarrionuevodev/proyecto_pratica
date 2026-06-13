import { describe, expect, it } from "vitest";

import {
  ACTUACION_ROW_ERROR_KEY_MAP,
  normalizeActuacionRowErrors,
} from "./submitActuacionRow";

describe("submitActuacionRow error map", () => {
  it("mapea claves Glide españolas a snake_case del modal", () => {
    const mapped = normalizeActuacionRowErrors({
      Contraproducencia: "Requerida",
      "Acta inspección": "Inválida",
    });
    expect(mapped.contraproducencia).toBe("Requerida");
    expect(mapped.acta_inspeccion_num).toBe("Inválida");
  });

  it("pasa claves pydantic snake_case sin cambio", () => {
    const mapped = normalizeActuacionRowErrors({
      rubro_nombre: "Rubro obligatorio",
      acta_comprobacion_num: "Número inválido",
    });
    expect(mapped.rubro_nombre).toBe("Rubro obligatorio");
    expect(mapped.acta_comprobacion_num).toBe("Número inválido");
  });

  it("mapea actas anidadas a celda de inspección", () => {
    const mapped = normalizeActuacionRowErrors({
      "actas.0.numero": "Revisá las actas cargadas",
    });
    expect(mapped.acta_inspeccion_num).toBe("Revisá las actas cargadas");
  });

  it("incluye alias nro_acta en el mapa", () => {
    expect(ACTUACION_ROW_ERROR_KEY_MAP.nro_acta_notificacion).toBe("acta_notificacion_num");
  });
});
