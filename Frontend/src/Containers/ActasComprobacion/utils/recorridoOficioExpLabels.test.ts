import { describe, expect, it } from "vitest";
import {
  recCompOficioExpMotivoChips,
  recOficioExpDetalleChips,
  recOficioExpItemLabel,
} from "./recorridoOficioExpLabels";
import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";

describe("recorridoOficioExpLabels", () => {
  it("renderiza oficio y expediente por ítem en oficios_resumen", () => {
    expect(
      recOficioExpItemLabel({
        numero_oficio: "3489",
        anio_oficio: 2026,
        oficio_texto: "3489/2026",
        numero_expediente: "012388",
        anio_expediente: 2026,
        expediente_texto: "012388/2026",
      })
    ).toBe("Oficio 3489/2026 · Exp. 012388/2026");
  });

  it("detalle por oficio incluye OT y conclusión propias", () => {
    const chips = recOficioExpDetalleChips({
      oficio_texto: "3489/2026",
      expediente_texto: "012388/2026",
      orden_trabajo_numero: "7696",
      conclusion: "Cumple",
      resultado: "CUMPLE",
    });
    expect(chips).toEqual([
      "Oficio 3489/2026 · Exp. 012388/2026",
      "OT: 7696",
      "Conclusión: Cumple",
    ]);
  });

  it("muestra placeholders cuando faltan OT o conclusión", () => {
    const chips = recOficioExpDetalleChips({
      oficio_texto: "3490/2026",
      expediente_texto: "012389/2026",
    });
    expect(chips).toContain("OT: Sin OT");
    expect(chips).toContain("Conclusión: Sin conclusión");
  });

  it("columna muestra dos oficios con OT y conclusión distintas", () => {
    const row = {
      id: 1,
      estado_recorrido: "—",
      fecha_actuacion: null,
      orden_trabajo_numero: null,
      acta_comprobacion_num: "009345",
      comprobacion_motivo: "Higiene",
      rubro_nombre: null,
      calle: null,
      numero: null,
      oficios_resumen: [
        {
          oficio_texto: "3489/2026",
          expediente_texto: "012388/2026",
          orden_trabajo_numero: "7696",
          conclusion: "Cumple",
        },
        {
          oficio_texto: "3490/2026",
          expediente_texto: "012389/2026",
          orden_trabajo_numero: "7697",
          conclusion: "No cumple",
        },
      ],
    } as IComprobacionRecorridoRow;

    const chips = recCompOficioExpMotivoChips(row);
    expect(chips).toContain("Comp. 009345");
    expect(chips).toContain("Oficio 3489/2026 · Exp. 012388/2026");
    expect(chips).toContain("OT: 7696");
    expect(chips).toContain("Conclusión: Cumple");
    expect(chips).toContain("Oficio 3490/2026 · Exp. 012389/2026");
    expect(chips).toContain("OT: 7697");
    expect(chips).toContain("Conclusión: No cumple");
    expect(chips.filter((c) => c.includes("undefined"))).toHaveLength(0);
    expect(chips.filter((c) => c.includes("null"))).toHaveLength(0);
  });
});
