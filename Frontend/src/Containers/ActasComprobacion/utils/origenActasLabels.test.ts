import { describe, expect, it } from "vitest";

import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import {
  chipsOrigenActasOficio,
  debeMostrarBloqueOrigenVerActuacion,
  exportCamposOrigenActasOficio,
  filasActasComprobacionOrigen,
  filasActasRatificadasOficio,
  filasOrigenActasVerActuacion,
  origenActasTieneContenido,
} from "./origenActasLabels";
import { mapRecorridoRow } from "./comprobacionesExportMappers";
import {
  buildComprobacionesNormalizedExcelRows,
  RECORRIDO_EXCEL_COLUMNS,
} from "./comprobacionesExportNormalizedRows";
import { buildComprobacionesVisualPdfRows } from "./comprobacionesExportVisualRows";
import { recorridoReinspeccionChips } from "./recorridoOficioExpLabels";

const ORIGEN_AMBOS = {
  actuacion_origen_id: 10,
  acta_decomiso_num: "004567",
  decomiso_kilos_total: 18.5,
  acta_clausura_num: "000832",
};

describe("origenActasLabels", () => {
  it("Ratificación de decomiso muestra acta y kilos ratificados", () => {
    const fuente = {
      tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO",
      origen_actas: ORIGEN_AMBOS,
    };
    expect(chipsOrigenActasOficio(fuente)).toEqual([
      "Acta de decomiso ratificada: N.º 004567",
      "Kilos ratificados: 18,5 kg",
    ]);
    expect(filasActasRatificadasOficio(fuente)).toEqual([
      { etiqueta: "Acta de decomiso ratificada", valor: "N.º 004567" },
      { etiqueta: "Kilos ratificados", valor: "18,5 kg" },
    ]);
    expect(chipsOrigenActasOficio(fuente).join(" ")).not.toContain("000832");
  });

  it("Ratificación de clausura muestra solo acta de clausura", () => {
    const fuente = {
      tipo_iniciador: "RATIFICACION_CLAUSURA_OFICIO",
      origen_actas: ORIGEN_AMBOS,
    };
    expect(chipsOrigenActasOficio(fuente)).toEqual(["Acta de clausura ratificada: N.º 000832"]);
    expect(filasActasRatificadasOficio(fuente)).toEqual([
      { etiqueta: "Acta de clausura ratificada", valor: "N.º 000832" },
    ]);
    expect(chipsOrigenActasOficio(fuente).join(" ")).not.toMatch(/decomiso/i);
  });

  it("Verificar e informar no muestra acta ni kilos ratificados", () => {
    const fuente = {
      tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
      origen_actas: ORIGEN_AMBOS,
    };
    expect(chipsOrigenActasOficio(fuente)).toEqual([]);
    expect(filasActasRatificadasOficio(fuente)).toEqual([]);
    expect(filasActasComprobacionOrigen(ORIGEN_AMBOS).length).toBeGreaterThan(0);
  });

  it("sin antecedentes no genera chips ni filas", () => {
    const vacio = {
      actuacion_origen_id: 10,
      acta_decomiso_num: null,
      decomiso_kilos_total: null,
      acta_clausura_num: null,
    };
    expect(origenActasTieneContenido(vacio)).toBe(false);
    expect(chipsOrigenActasOficio({ tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO", origen_actas: vacio })).toEqual([]);
    expect(filasActasComprobacionOrigen(vacio)).toEqual([]);
  });

  it("Verificar e informar con decomiso propio de visita usa solo origen_actas", () => {
    const chips = chipsOrigenActasOficio({
      tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
      origen_actas: {
        actuacion_origen_id: 10,
        acta_decomiso_num: "004567",
        decomiso_kilos_total: 18.5,
        acta_clausura_num: null,
      },
      ejecucion_reinspeccion: {
        tipo_inspeccion_labrada: "VERIFICAR E INFORMAR",
        acta_decomiso_num: "009999",
        decomiso_kilos_total: 99.9,
      },
    });
    expect(chips).toEqual([]);
    expect(chips.join(" ")).not.toContain("009999");
    expect(chips.join(" ")).not.toContain("99,9");
    expect(chips.join(" ")).not.toContain("004567");
  });

  it("recorrido Reinspección agrega chips de actas ratificadas bajo el tipo", () => {
    const row: IComprobacionRecorridoRow = {
      id: 1,
      estado_recorrido: "ok",
      fecha_actuacion: "2026-08-10",
      orden_trabajo_numero: "1",
      acta_comprobacion_num: "1",
      comprobacion_motivo: null,
      rubro_nombre: null,
      calle: null,
      numero: null,
      oficios_resumen: [
        {
          oficio_texto: "100/2026",
          tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO",
          estado_iniciador: "CUMPLIDO",
          resultado: "CUMPLE",
          origen_actas: {
            actuacion_origen_id: 10,
            acta_decomiso_num: "004567",
            decomiso_kilos_total: 18.5,
            acta_clausura_num: null,
          },
        },
      ],
    };
    const chips = recorridoReinspeccionChips(row);
    expect(chips).toContain("Ratificación de decomiso");
    expect(chips).toContain("Acta de decomiso ratificada: N.º 004567");
    expect(chips).toContain("Kilos ratificados: 18,5 kg");
  });
});

describe("origenActas export PDF/XLSX", () => {
  it("Excel incorpora actas y kilos ratificados según tipo; Verificar e informar queda vacío", () => {
    const mapped = mapRecorridoRow({
      id: 1,
      estado_recorrido: "ok",
      fecha_actuacion: "2026-08-10",
      orden_trabajo_numero: "1",
      acta_comprobacion_num: "456",
      comprobacion_motivo: null,
      rubro_nombre: "Panadería",
      calle: "San Martín",
      numero: "100",
      oficios_resumen: [
        {
          oficio_texto: "432/2026",
          tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO",
          origen_actas: ORIGEN_AMBOS,
        },
        {
          oficio_texto: "1989/2026",
          tipo_iniciador: "RATIFICACION_CLAUSURA_OFICIO",
          origen_actas: ORIGEN_AMBOS,
        },
        {
          oficio_texto: "9/2026",
          tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
          origen_actas: ORIGEN_AMBOS,
        },
      ],
    });
    const excel = buildComprobacionesNormalizedExcelRows([mapped], "recorrido");
    expect(RECORRIDO_EXCEL_COLUMNS.slice(-5)).toEqual([
      "Fecha reinspección",
      "OT reinspección",
      "Acta clausura ratificada",
      "Acta decomiso ratificada",
      "Kilos ratificados",
    ]);
    expect(Object.keys(excel[0])).toEqual([...RECORRIDO_EXCEL_COLUMNS]);
    expect(excel[0]["Acta decomiso ratificada"]).toBe("004567");
    expect(excel[0]["Kilos ratificados"]).toBe("18,5");
    expect(excel[0]["Acta clausura ratificada"]).toBe("");
    expect(excel[1]["Acta clausura ratificada"]).toBe("000832");
    expect(excel[1]["Acta decomiso ratificada"]).toBe("");
    expect(excel[1]["Kilos ratificados"]).toBe("");
    expect(excel[2]["Acta clausura ratificada"]).toBe("");
    expect(excel[2]["Acta decomiso ratificada"]).toBe("");
    expect(excel[2]["Kilos ratificados"]).toBe("");
  });

  it("PDF incluye tipo final y campos de origen; vacío no inventa 0", () => {
    const mapped = mapRecorridoRow({
      id: 1,
      estado_recorrido: "ok",
      fecha_actuacion: "2026-08-10",
      orden_trabajo_numero: "1",
      acta_comprobacion_num: "456",
      comprobacion_motivo: null,
      rubro_nombre: null,
      calle: null,
      numero: null,
      oficios_resumen: [
        {
          oficio_texto: "432/2026",
          tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
          origen_actas: ORIGEN_AMBOS,
        },
        {
          oficio_texto: "9/2026",
          tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO",
          origen_actas: {
            actuacion_origen_id: 10,
            acta_decomiso_num: null,
            decomiso_kilos_total: null,
            acta_clausura_num: null,
          },
        },
      ],
    });
    const [pdf] = buildComprobacionesVisualPdfRows([mapped]);
    expect(pdf.tipoConclusion).toContain("Verificar e informar");
    expect(pdf.tipoConclusion).toContain("Acta de decomiso origen: N.º 004567");
    expect(pdf.tipoConclusion).toContain("Kilos decomiso origen: 18,5");
    expect(pdf.tipoConclusion).toContain("Acta de clausura origen: N.º 000832");
    expect(pdf.tipoConclusion).not.toMatch(/Kilos decomiso origen: 0\b/);
    expect(exportCamposOrigenActasOficio({ tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO" }).kilosDecomisoOrigen).toBe(
      ""
    );
  });
});

describe("origenActas Ver actuación", () => {
  it("visita de ratificación muestra filas de origen", () => {
    expect(
      debeMostrarBloqueOrigenVerActuacion({
        actuacionId: 20,
        tipoActuacion: "RATIFICACION DE DECOMISO",
        origenActas: ORIGEN_AMBOS,
      })
    ).toBe(true);
    const filas = filasOrigenActasVerActuacion(ORIGEN_AMBOS, "RATIFICACION DE DECOMISO");
    expect(filas).toEqual([
      { etiqueta: "N.º acta de decomiso", valor: "004567" },
      { etiqueta: "Kilos ratificados", valor: "18,5 kg" },
    ]);
  });

  it("ancla o inspección común no muestra el bloque", () => {
    expect(
      debeMostrarBloqueOrigenVerActuacion({
        actuacionId: 10,
        tipoActuacion: "INSPECCION",
        origenActas: ORIGEN_AMBOS,
      })
    ).toBe(false);
    expect(
      debeMostrarBloqueOrigenVerActuacion({
        actuacionId: 10,
        tipoActuacion: "RATIFICACION DE DECOMISO",
        origenActas: ORIGEN_AMBOS,
      })
    ).toBe(false);
  });
});
