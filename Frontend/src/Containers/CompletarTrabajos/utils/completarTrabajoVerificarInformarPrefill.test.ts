import { describe, expect, it } from "vitest";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { buildCompletarTrabajoCierreBodyFromInline } from "./buildCompletarTrabajoCierreBody";
import { operativoHydrationFromRow } from "./completarTrabajoVerificarInformarPrefill";

describe("completarTrabajoVerificarInformarPrefill", () => {
  it("precarga documento y nombre desde fila de origen", () => {
    const row = {
      ruta_item_id: 1,
      calle: "San Martín",
      numero: "100",
      rubro_nombre: "Panadería",
      doc_nro: "30111222",
      contrib_apellido: "Gómez",
      contrib_nombre: "Ana",
    } as ICompletarTrabajoPendienteRow;
    const h = operativoHydrationFromRow(row);
    expect(h.docNro).toBe("30111222");
    expect(h.contribApellido).toBe("Gómez");
    expect(h.contribNombre).toBe("Ana");
  });
});

describe("buildCompletarTrabajoCierreBody verificar e informar", () => {
  it("incluye documento/nombre en payload aunque no se hayan editado explícitamente", () => {
    const row = {
      ruta_item_id: 9,
      tipo_iniciador: "REINSPECCION_OFICIO",
      calle: "Calle",
      numero: "10",
      doc_nro: "20999888",
      contrib_apellido: "López",
      contrib_nombre: "María",
      rubro_nombre: "Carnicería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      {
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: "si",
        doc_nro: "20999888",
        contrib_apellido: "López",
        contrib_nombre: "María",
        rubro_nombre: "Carnicería",
        calle: "Calle",
        numero: "10",
        numero_tipo: "NUMERO",
        acta_inspeccion_num: "123456",
      },
      { includeTipoActuacion: true }
    );
    expect(body.doc_nro).toBe("20999888");
    expect(body.contrib_apellido).toBe("López");
    expect(body.contrib_nombre).toBe("María");
    expect(body.realizo_nueva_inspeccion).toBe(true);
    expect(body.tipo_actuacion).toBe("VERIFICAR E INFORMAR");
  });
});
