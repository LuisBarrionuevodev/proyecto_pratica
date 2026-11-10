import { describe, expect, it } from "vitest";
import {
  hydrateMotivosComprobacion,
  motivosComprobacionLecturaMultilinea,
  motivosComprobacionTexto,
  orderedMotivosComprobacion,
  primerMotivoComprobacionLegado,
} from "./motivosComprobacion";

describe("motivosComprobacion", () => {
  it("conserva el orden de carga y omite duplicados", () => {
    expect(orderedMotivosComprobacion(["B", "A", "B", " C "])).toEqual(["B", "A", "C"]);
  });

  it("hidrata el arreglo canónico antes que el escalar", () => {
    expect(
      hydrateMotivosComprobacion({
        motivos_comprobacion: ["Falta de Higiene", "Incumplimiento"],
        comprobacion_motivo: "Falta de Higiene",
      })
    ).toEqual(["Falta de Higiene", "Incumplimiento"]);
  });

  it("hidrata un histórico de un solo motivo desde el escalar", () => {
    expect(
      hydrateMotivosComprobacion({
        motivos_comprobacion: [],
        comprobacion_motivo: "Falta de Higiene",
      })
    ).toEqual(["Falta de Higiene"]);
  });

  it("no hidrata PENDIENTE", () => {
    expect(hydrateMotivosComprobacion({ comprobacion_motivo: "PENDIENTE" })).toEqual([]);
  });

  it("formatea compacto y con viñetas", () => {
    const list = ["Falta de Higiene", "Falta de Habilitación"];
    expect(motivosComprobacionTexto(list)).toBe("Falta de Higiene · Falta de Habilitación");
    expect(motivosComprobacionLecturaMultilinea(list)).toBe(
      "• Falta de Higiene\n• Falta de Habilitación"
    );
    expect(primerMotivoComprobacionLegado(list)).toBe("Falta de Higiene");
  });
});
