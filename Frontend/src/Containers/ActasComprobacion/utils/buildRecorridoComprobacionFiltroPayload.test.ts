import { describe, expect, it } from "vitest";
import {
  buildRecorridoComprobacionFiltroPayload,
  recorridoComprobacionHasPeriodChosen,
  recorridoPayloadToApiParams,
} from "./buildRecorridoComprobacionFiltroPayload";

const emptyForm = {
  periodMode: "month" as const,
  mes: "" as const,
  anio: "" as const,
  desde: null,
  hasta: null,
  distritoId: "" as const,
  actaComprobacion: "",
  calleQ: "",
  contribuyenteQ: "",
  oficioNumero: "",
  expedienteNumero: "",
  tipoFinal: "",
  combinarConPeriodo: false,
};

describe("buildRecorridoComprobacionFiltroPayload", () => {
  it("inicia sin mes/año aplicado", () => {
    expect(recorridoComprobacionHasPeriodChosen(emptyForm)).toBe(false);
  });

  it("buscar N° acta comprobación no envía mes/año por defecto", () => {
    const r = buildRecorridoComprobacionFiltroPayload({
      ...emptyForm,
      mes: 7,
      anio: 2026,
      actaComprobacion: "000123",
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      const api = recorridoPayloadToApiParams(r.payload);
      expect(api.omitirRangoFecha).toBe(true);
      expect(api.mes).toBeUndefined();
      expect(api.anio).toBeUndefined();
      expect(api.acta_comprobacion).toBe("000123");
    }
  });

  it("oficio/expediente sin período usa búsqueda global", () => {
    const r = buildRecorridoComprobacionFiltroPayload({
      ...emptyForm,
      oficioNumero: "45",
      expedienteNumero: "789",
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      const api = recorridoPayloadToApiParams(r.payload);
      expect(api.omitirRangoFecha).toBe(true);
      expect(api.oficio_numero).toBe("45");
      expect(api.expediente_numero).toBe("789");
    }
  });

  it("mes/año elegidos se envían en modo período", () => {
    const r = buildRecorridoComprobacionFiltroPayload({
      ...emptyForm,
      mes: 4,
      anio: 2024,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      const api = recorridoPayloadToApiParams(r.payload);
      expect(api.mes).toBe(4);
      expect(api.anio).toBe(2024);
      expect(api.omitirRangoFecha).toBeUndefined();
    }
  });

  it("combina período cuando el usuario lo pide", () => {
    const r = buildRecorridoComprobacionFiltroPayload({
      ...emptyForm,
      mes: 7,
      anio: 2026,
      calleQ: "San Martín",
      combinarConPeriodo: true,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      const api = recorridoPayloadToApiParams(r.payload);
      expect(api.mes).toBe(7);
      expect(api.anio).toBe(2026);
      expect(api.calle_q).toBe("San Martín");
    }
  });
});
