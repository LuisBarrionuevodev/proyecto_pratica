import { describe, expect, it } from "vitest";
import {
  filasActaComprobacionRecorrido,
  filasEstadoTramiteRecorrido,
  filasOficioRecorridoDocumental,
  recCompOficioExpMotivoChips,
  recOficioExpDetalleChips,
  recOficioExpItemLabel,
  recorridoColumnChips,
  recorridoHeaderReference,
  recorridoResultadoSeguimientoChips,
  recorridoVisitaResumenLinea,
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

  it("columna Recorrido muestra una línea por oficio con visita_resumen_texto", () => {
    const row = {
      id: 1,
      estado_recorrido: "Verificar e informar — visita realizada",
      oficios_resumen: [
        {
          visita_resumen_texto: "Oficio 432/2026 · Verificar e informar · Realizada",
        },
        {
          visita_resumen_texto: "Oficio 1989/2026 · Ratificación de clausura · Realizada",
        },
      ],
    } as IComprobacionRecorridoRow;

    expect(recorridoColumnChips(row)).toEqual([
      "Oficio 432/2026 · Verificar e informar · Realizada",
      "Oficio 1989/2026 · Ratificación de clausura · Realizada",
    ]);
  });

  it("columna Recorrido con un oficio usa visita_resumen_texto", () => {
    const row = {
      id: 1,
      oficios_resumen: [{ visita_resumen_texto: "Oficio 100/2026 · Reinspección · Realizada" }],
    } as IComprobacionRecorridoRow;
    expect(recorridoColumnChips(row)).toEqual(["Oficio 100/2026 · Reinspección · Realizada"]);
  });

  it("columna Recorrido sin oficios usa estado_recorrido", () => {
    const row = {
      id: 1,
      estado_recorrido: "Oficio cargado — sin reinspección programada",
    } as IComprobacionRecorridoRow;
    expect(recorridoColumnChips(row)).toEqual(["Oficio cargado — sin reinspección programada"]);
  });

  it("fallback frontend arma no realizada con motivo", () => {
    expect(
      recorridoVisitaResumenLinea({
        oficio_texto: "432/2026",
        iniciador_id: 1,
        estado_iniciador: "CUMPLIDO",
        estado_ejecucion: "NO_REALIZADO",
        motivo_no_realizado: "LOCAL_CERRADO",
      })
    ).toBe("Oficio 432/2026 · No realizada · Local cerrado");
  });

  it("Resultado / seguimiento: sin oficios es guión", () => {
    expect(recorridoResultadoSeguimientoChips({ id: 1 } as IComprobacionRecorridoRow)).toEqual(["—"]);
  });

  it("Resultado / seguimiento: oficio pendiente", () => {
    expect(
      recorridoResultadoSeguimientoChips({
        id: 1,
        oficios_resumen: [{ oficio_texto: "100/2026", iniciador_id: 4, estado_iniciador: "PENDIENTE" }],
      } as IComprobacionRecorridoRow)
    ).toEqual(["Pendiente de reinspección"]);
  });

  it("Resultado / seguimiento: visita sin resultado no inventa cumple", () => {
    expect(
      recorridoResultadoSeguimientoChips({
        id: 1,
        oficios_resumen: [
          {
            oficio_texto: "100/2026",
            estado_iniciador: "CUMPLIDO",
            estado_ejecucion: "REALIZADO",
            resultado: null,
            ejecucion_reinspeccion: { actuacion_id: 9 },
          },
        ],
      } as IComprobacionRecorridoRow)
    ).toEqual(["Reinspección realizada"]);
  });

  it("Resultado / seguimiento: CUMPLE y NO_CUMPLE separados", () => {
    expect(
      recorridoResultadoSeguimientoChips({
        id: 1,
        oficios_resumen: [
          { oficio_texto: "432/2026", resultado: "CUMPLE", resultado_cumplimiento_oficio: "CUMPLE" },
          { oficio_texto: "1989/2026", resultado: "NO_CUMPLE", resultado_cumplimiento_oficio: "NO_CUMPLE" },
        ],
      } as IComprobacionRecorridoRow)
    ).toEqual(["432/2026 · Cumple", "1989/2026 · No cumple"]);
  });

  it("Estado del trámite resume sin mezclar oficios", () => {
    const filas = filasEstadoTramiteRecorrido(
      {
        id: 1,
        estado_recorrido: "Reinspección cumplida",
        oficios_resumen: [
          { oficio_texto: "432/2026", resultado: "CUMPLE" },
          { oficio_texto: "1989/2026", resultado: "NO_CUMPLE" },
        ],
      } as IComprobacionRecorridoRow,
      {
        resultado_final: { estado_recorrido: "Reinspección cumplida" },
        oficios_resumen: [
          { oficio_texto: "432/2026", resultado: "CUMPLE" },
          { oficio_texto: "1989/2026", resultado: "NO_CUMPLE" },
        ],
      }
    );
    expect(filas.find((f) => f.etiqueta === "Oficio asociado")?.valor).toBe("432/2026 · 1989/2026");
    expect(filas.find((f) => f.etiqueta === "Resultado final")?.valor).toBe("—");
  });

  it("cabecera documental del acta incluye acta, fecha, OT, domicilio e inspectores", () => {
    const filas = filasActaComprobacionRecorrido({
      id: 1,
      acta_comprobacion_num: "009345",
      fecha_actuacion: "2026-07-10",
      orden_trabajo_numero: "123456",
      calle: "San Martín",
      numero: "450",
      inspector1: "García",
      inspector2: "López",
    } as IComprobacionRecorridoRow);
    expect(filas.find((f) => f.etiqueta === "N.º de acta")?.valor).toBe("009345");
    expect(filas.find((f) => f.etiqueta === "Fecha")?.valor).toBe("2026-07-10");
    expect(filas.find((f) => f.etiqueta === "Orden de trabajo")?.valor).toBe("123456");
    expect(filas.find((f) => f.etiqueta === "Domicilio")?.valor).toBe("San Martín 450");
    expect(filas.find((f) => f.etiqueta === "Inspectores")?.valor).toBe("García · López");
    expect(
      recorridoHeaderReference(
        {
          id: 1,
          acta_comprobacion_num: "009345",
          fecha_actuacion: "2026-07-10",
          orden_trabajo_numero: "123456",
        } as IComprobacionRecorridoRow,
        null
      )
    ).toBe("Acta N.º 009345 · 2026-07-10 · OT 123456");
  });

  it("cada oficio conserva su propio estado y no hereda la visita ajena", () => {
    const cumple = {
      oficio_texto: "432/2026",
      causa: "Higiene",
      numero_expediente: "1",
      anio_expediente: 2026,
      resultado: "CUMPLE",
      resultado_cumplimiento_oficio: "CUMPLE",
      ejecucion_reinspeccion: {
        fecha_actuacion: "2026-08-01",
        orden_trabajo_numero: "111",
        inspectores_texto: "Pérez",
        acta_inspeccion_num: "50",
      },
    };
    const noCumple = {
      oficio_texto: "1989/2026",
      resultado: "NO_CUMPLE",
      resultado_cumplimiento_oficio: "NO_CUMPLE",
      iniciador_id: 9,
      estado_iniciador: "PENDIENTE",
    };
    const a = filasOficioRecorridoDocumental(cumple, null, 2);
    const b = filasOficioRecorridoDocumental(noCumple, {
      reinspeccion_por_oficio: {
        iniciador_id: 4,
        ejecucion_reinspeccion: { fecha_actuacion: "2026-09-99", inspectores_texto: "Ajeno" },
      },
    }, 2);
    expect(a.find((f) => f.etiqueta === "Estado")?.valor).toBe("Cumple");
    expect(a.find((f) => f.etiqueta === "Fecha de reinspección")?.valor).toBe("2026-08-01");
    expect(a.find((f) => f.etiqueta === "Acta de inspección")?.valor).toBe("50");
    expect(a.find((f) => f.etiqueta === "Causa")?.valor).toBe("Higiene");
    expect(b.find((f) => f.etiqueta === "Estado")?.valor).toBe("No cumple");
    expect(b.find((f) => f.etiqueta === "Fecha de reinspección")).toBeUndefined();
    expect(b.some((f) => f.valor === "Ajeno")).toBe(false);
  });

  it("oficio pendiente no inventa cumple ni muestra reinspección vacía", () => {
    const filas = filasOficioRecorridoDocumental(
      { oficio_texto: "100/2026", iniciador_id: 4, estado_iniciador: "PENDIENTE" },
      null,
      1
    );
    expect(filas.find((f) => f.etiqueta === "Estado")?.valor).toBe("Pendiente de reinspección");
    expect(filas.find((f) => f.etiqueta === "Fecha de reinspección")).toBeUndefined();
    expect(filas.find((f) => f.etiqueta === "Resultado final")).toBeUndefined();
  });
});
