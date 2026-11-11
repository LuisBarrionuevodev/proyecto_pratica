import { describe, expect, it } from "vitest";

import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { mapRecorridoRow } from "./comprobacionesExportMappers";
import { buildComprobacionesNormalizedExcelRows } from "./comprobacionesExportNormalizedRows";
import { buildComprobacionesVisualPdfRows } from "./comprobacionesExportVisualRows";
import {
  recOficioDocumentalAgrupado,
  recOficioExpOtOrigenMotivosChips,
} from "./recorridoOficioExpLabels";

function row(overrides: Partial<IComprobacionRecorridoRow> = {}): IComprobacionRecorridoRow {
  return {
    id: 1,
    estado_recorrido: "—",
    fecha_actuacion: "2026-05-27",
    orden_trabajo_numero: "099001",
    acta_comprobacion_num: "009345",
    comprobacion_motivo: "No permite la inspección",
    motivos_comprobacion: ["No permite la inspección", "Falta de higiene"],
    oficios_resumen: [],
    ...overrides,
  };
}

const OFICIO_1 = {
  oficio_texto: "98789/2026",
  expediente_texto: "098789/2026",
  causa: "98789",
};
const OFICIO_2 = {
  oficio_texto: "97897/2026",
  expediente_texto: "097896/2026",
  causa: "97897",
};
const OFICIO_3 = {
  oficio_texto: "11111/2026",
  expediente_texto: "011111/2026",
  causa: "11111",
};

describe("HOTFIX V1.1-RECORRIDO-COMP.1C — columna documental", () => {
  it("1. un oficio mantiene formato compacto, sin encabezados OFICIO/MOTIVOS", () => {
    const r = row({ oficios_resumen: [OFICIO_1] });
    expect(recOficioDocumentalAgrupado(r)).toBeNull();
    expect(recOficioExpOtOrigenMotivosChips(r)).toEqual([
      "Oficio 98789/2026",
      "Exp. 098789/2026",
      "OT origen 099001",
      "Causa 98789",
      "No permite la inspección · Falta de higiene",
    ]);
  });

  it("2. dos y tres oficios: grupos inequívocos, OT origen una vez, causa propia", () => {
    const dos = recOficioDocumentalAgrupado(row({ oficios_resumen: [OFICIO_1, OFICIO_2] }));
    expect(dos?.otOrigen).toBe("OT origen 099001");
    expect(dos?.grupos).toEqual([
      {
        titulo: "OFICIO 1",
        chips: ["Oficio 98789/2026", "Exp. 098789/2026", "Causa 98789"],
      },
      {
        titulo: "OFICIO 2",
        chips: ["Oficio 97897/2026", "Exp. 097896/2026", "Causa 97897"],
      },
    ]);
    expect(dos?.motivos).toBe("No permite la inspección · Falta de higiene");

    const tres = recOficioDocumentalAgrupado(row({ oficios_resumen: [OFICIO_1, OFICIO_2, OFICIO_3] }));
    expect(tres?.grupos.map((g) => g.titulo)).toEqual(["OFICIO 1", "OFICIO 2", "OFICIO 3"]);
    expect(tres?.grupos[2].chips).toContain("Oficio 11111/2026");
  });

  it("3. sin OT origen no deja hueco", () => {
    const g = recOficioDocumentalAgrupado(
      row({ orden_trabajo_numero: null, oficios_resumen: [OFICIO_1, OFICIO_2] })
    );
    expect(g?.otOrigen).toBe("");
  });

  it("4. motivos múltiples una sola vez al final", () => {
    const g = recOficioDocumentalAgrupado(row({ oficios_resumen: [OFICIO_1, OFICIO_2] }));
    expect(g?.motivos).toBe("No permite la inspección · Falta de higiene");
    const joined = g?.grupos.flatMap((x) => x.chips).join(" ") ?? "";
    expect(joined).not.toMatch(/No permite la inspección/);
  });

  it("7. PDF/XLSX no cambian por el agrupado visual", () => {
    const r = row({ oficios_resumen: [OFICIO_1, OFICIO_2] });
    const mapped = mapRecorridoRow(r);
    const [pdf] = buildComprobacionesVisualPdfRows([mapped]);
    const excel = buildComprobacionesNormalizedExcelRows([mapped], "recorrido");
    expect(pdf.oficioExpOtMotivos).toContain("Oficio 98789/2026");
    expect(pdf.oficioExpOtMotivos).toContain("Oficio 97897/2026");
    expect(pdf.oficioExpOtMotivos).not.toContain("OFICIO 1");
    expect(excel).toHaveLength(2);
    expect(excel[0]["N.º oficio"]).toBe("98789/2026");
    expect(excel[1]["N.º oficio"]).toBe("97897/2026");
  });
});
