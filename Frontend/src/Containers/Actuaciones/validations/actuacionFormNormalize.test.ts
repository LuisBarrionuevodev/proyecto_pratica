import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  commitActaNumInputValue,
  detectActasClearedByUser,
  normalizeActuacionRowForCrudSubmit,
  sanitizeEmptyActasForPut,
  validateAndNormalizeActaNum,
  validateDocNro,
} from "./actuacionFormNormalize";

const baseRow: IActuacionListItem = {
  id: 1,
  orden_trabajo_numero: "123456",
  fecha_actuacion: "2026-05-10",
  tipo_actuacion: "INSPECCION",
  rubro_nombre: "Bar",
  inspector1: "García",
  inspector2: "López",
  inspector3: null,
  calle: "San Martín",
  numero: "100",
  doc_nro: "20345678901",
  contrib_apellido: "Pérez",
  contrib_nombre: "Juan",
  contraproducencia: null,
  acta_inspeccion_num: "000042",
  acta_notificacion_num: null,
  notificacion_motivo_1: null,
  notificacion_motivo_2: null,
  notificacion_motivo_3: null,
  acta_comprobacion_num: null,
  comprobacion_motivo: null,
  acta_clausura_num: null,
  acta_decomiso_num: null,
  decomiso_kilos_total: null,
  expediente_numero: null,
  expediente_anio: null,
  oficio_numero: null,
  oficio_anio: null,
  oficio_causa: null,
};

describe("commitActaNumInputValue", () => {
  it("normaliza 25 a 000025 al commit (blur/guardar)", () => {
    expect(commitActaNumInputValue("25")).toBe("000025");
  });

  it("vacío retorna null sin padStart", () => {
    expect(commitActaNumInputValue("")).toBeNull();
    expect(commitActaNumInputValue("   ")).toBeNull();
  });

  it("no aplica padStart mientras se escribe (solo al commit)", () => {
    expect(validateAndNormalizeActaNum("2").ok).toBe(true);
    expect(commitActaNumInputValue("2")).toBe("000002");
  });
});

describe("sanitizeEmptyActasForPut", () => {
  it("omite acta de inspección vacía", () => {
    const out = sanitizeEmptyActasForPut({ ...baseRow, acta_inspeccion_num: "" });
    expect(out.acta_inspeccion_num).toBeNull();
  });

  it("omite notificación sin número ni motivos", () => {
    const out = sanitizeEmptyActasForPut({
      ...baseRow,
      acta_notificacion_num: "",
      notificacion_motivo_1: null,
      notificacion_motivo_2: null,
      notificacion_motivo_3: null,
    });
    expect(out.acta_notificacion_num).toBeNull();
    expect(out.notificacion_motivo_1).toBeNull();
  });

  it("conserva notificación con motivo aunque el número esté vacío", () => {
    const out = sanitizeEmptyActasForPut({
      ...baseRow,
      acta_notificacion_num: "",
      notificacion_motivo_1: "Falta habilitación",
    });
    expect(out.acta_notificacion_num).toBeNull();
    expect(out.notificacion_motivo_1).toBe("Falta habilitación");
  });

  it("omite decomiso sin número ni kilos", () => {
    const out = sanitizeEmptyActasForPut({
      ...baseRow,
      acta_decomiso_num: "",
      decomiso_kilos_total: null,
    });
    expect(out.acta_decomiso_num).toBeNull();
    expect(out.decomiso_kilos_total).toBeNull();
  });
});

describe("normalizeActuacionRowForCrudSubmit", () => {
  it("acta 25 se guarda como 000025", () => {
    const normalized = normalizeActuacionRowForCrudSubmit({ ...baseRow, acta_inspeccion_num: "25" });
    expect(normalized.acta_inspeccion_num).toBe("000025");
  });

  it("acta vacía no queda en payload normalizado", () => {
    const normalized = normalizeActuacionRowForCrudSubmit({ ...baseRow, acta_clausura_num: "  " });
    expect(normalized.acta_clausura_num).toBeNull();
  });
});

describe("detectActasClearedByUser", () => {
  it("detecta inspección vaciada por el usuario", () => {
    const original = { ...baseRow, acta_inspeccion_num: "000123" };
    const draft = { ...original, acta_inspeccion_num: "" };
    expect(detectActasClearedByUser(original, draft)).toEqual([
      { tipo: "INSPECCION", field: "acta_inspeccion_num" },
    ]);
  });

  it("acta nueva vacía no genera quitar-acta", () => {
    const original = { ...baseRow, acta_inspeccion_num: null };
    const draft = { ...original, acta_inspeccion_num: "" };
    expect(detectActasClearedByUser(original, draft)).toEqual([]);
  });

  it("notificación vaciada limpia motivos en sanitize", () => {
    const out = sanitizeEmptyActasForPut({
      ...baseRow,
      acta_notificacion_num: "",
      notificacion_motivo_1: null,
      notificacion_motivo_2: null,
      notificacion_motivo_3: null,
    });
    expect(out.acta_notificacion_num).toBeNull();
    expect(out.notificacion_motivo_1).toBeNull();
  });

  it("FIX.6.2 — detecta inspección y notificación vaciadas", () => {
    const original = {
      ...baseRow,
      acta_inspeccion_num: "5032",
      acta_notificacion_num: "812",
    };
    const draft = {
      ...original,
      acta_inspeccion_num: "",
      acta_notificacion_num: "",
      notificacion_motivo_1: null,
    };
    expect(detectActasClearedByUser(original, draft).map((a) => a.tipo)).toEqual([
      "INSPECCION",
      "NOTIFICACION",
    ]);
  });

  it("FIX.8 — reinspección notificación no marca notificación origen para quitar", () => {
    const original = {
      ...baseRow,
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      acta_inspeccion_num: "5032",
      acta_notificacion_num: "812",
    };
    const draft = {
      ...original,
      acta_inspeccion_num: "",
      acta_notificacion_num: "",
    };
    expect(detectActasClearedByUser(original, draft).map((a) => a.tipo)).toEqual(["INSPECCION"]);
  });
});

describe("validateDocNro en normalize", () => {
  it("acepta mínimo 7 dígitos", () => {
    expect(validateDocNro("1234567")).toBeNull();
    expect(validateDocNro("20345678901")).toBeNull();
  });

  it("rechaza menos de 7 dígitos y separadores", () => {
    expect(validateDocNro("123456")).toBeTruthy();
    expect(validateDocNro("20-34567890-1")).toBeTruthy();
    expect(validateDocNro("20.345.678")).toBeTruthy();
  });
});
