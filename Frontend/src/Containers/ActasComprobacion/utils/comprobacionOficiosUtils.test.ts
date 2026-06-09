import { describe, expect, it } from "vitest";

import type { IComprobacionDocumentalResponse, OficioComprobacionItem } from "../../../api/actuacionesPendientesApi";
import {
  documentalDesdeOficioItem,
  mergeOficiosConLegacyDocumental,
  oficioComprobacionEtiquetaCompacta,
  oficioComprobacionSubtituloIniciador,
} from "./comprobacionOficiosUtils";

const baseEdicion: IComprobacionDocumentalResponse["edicion"] = {
  comprobacion_usada_como_iniciador: false,
  puede_editar_expediente_envio: true,
  puede_editar_bloque_oficio: true,
  puede_eliminar_expediente_envio: true,
  puede_eliminar_bloque_oficio: true,
  motivos_bloqueo_expediente_envio: [],
  motivos_bloqueo_oficio: [],
  motivos_bloqueo_eliminar_expediente_envio: [],
  motivos_bloqueo_eliminar_bloque_oficio: [],
};

describe("comprobacionOficiosUtils", () => {
  it("formatea etiqueta compacta con oficio y expediente", () => {
    const item: OficioComprobacionItem = {
      id: 1,
      numero_oficio: "204",
      anio: 2026,
      expediente_numero: "123",
      expediente_anio: 2026,
    };
    expect(oficioComprobacionEtiquetaCompacta(item)).toBe("Oficio 204/2026 · Exp. 123/2026");
  });

  it("muestra estado de iniciador solo si viene en payload", () => {
    expect(oficioComprobacionSubtituloIniciador({ id: 1, numero_oficio: "1", anio: 2026 })).toBeNull();
    expect(
      oficioComprobacionSubtituloIniciador({ id: 1, numero_oficio: "1", anio: 2026, iniciador_estado: "PENDIENTE" })
    ).toBe("Iniciador Pendiente");
  });

  it("usa fallback legacy cuando la lista está vacía", () => {
    const doc: IComprobacionDocumentalResponse = {
      actuacion_id: 10,
      comprobacion_id: 5,
      expediente_envio: null,
      oficio: {
        id: 7,
        numero_oficio: "100",
        anio: 2026,
        fecha_oficio: "2026-04-01",
        causa: "X",
        juzgado_id: 1,
        juzgado_nombre: "Juzgado 1",
      },
      expediente_respuesta: {
        id: 8,
        numero_expediente: "50",
        anio: "2026",
        fecha_expediente: "2026-04-01",
        tipo_expediente: "RESPUESTA_OFICIO",
        oficio_id: 7,
      },
      edicion: baseEdicion,
    };
    const merged = mergeOficiosConLegacyDocumental([], doc);
    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe(7);
    expect(merged[0].expediente_numero).toBe("50");
  });

  it("arma documental por oficio seleccionado", () => {
    const base: IComprobacionDocumentalResponse = {
      actuacion_id: 10,
      comprobacion_id: 5,
      expediente_envio: null,
      oficio: null,
      expediente_respuesta: null,
      edicion: baseEdicion,
    };
    const item: OficioComprobacionItem = {
      id: 9,
      numero_oficio: "258",
      anio: 2026,
      expediente_id: 11,
      expediente_numero: "130",
      expediente_anio: 2026,
      tribunal: "Tribunal X",
    };
    const snap = documentalDesdeOficioItem(base, item);
    expect(snap?.oficio?.id).toBe(9);
    expect(snap?.expediente_respuesta?.numero_expediente).toBe("130");
  });
});
