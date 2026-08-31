import { describe, expect, it, vi, beforeEach } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { mergeActuacionAfterOficioCorrection } from "./mergeActuacionAfterOficioCorrection";
import { submitActuacionRow } from "./submitActuacionRow";

vi.mock("../../../api/gridApi", () => ({
  validateRow: vi.fn(),
}));

vi.mock("../../../api/actuacionesApi", () => ({
  updateActuacion: vi.fn(),
}));

vi.mock("../../../api/actuacionesListApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/actuacionesListApi")>();
  return { ...mod, postQuitarActaCanalActas: vi.fn() };
});

import { validateRow } from "../../../api/gridApi";
import { updateActuacion } from "../../../api/actuacionesApi";

const mockedValidateRow = vi.mocked(validateRow);
const mockedUpdateActuacion = vi.mocked(updateActuacion);

function baseOficioRow(): IActuacionListItem {
  return {
    id: 99,
    orden_trabajo_numero: "100001",
    fecha_actuacion: "2026-06-10",
    tipo_actuacion: "VERIFICAR E INFORMAR",
    rubro_nombre: "Bar",
    inspector1: "García",
    calle: "San Martín",
    numero: "100",
    doc_nro: "20345678901",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    contraproducencia: "LOCAL CERRADO",
    documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
    realizo_nueva_inspeccion: false,
  } as IActuacionListItem;
}

describe("pipeline corrección Oficio → submit Actuaciones", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedValidateRow.mockResolvedValue({ ok: true, errors: {}, normalized: {} } as any);
    mockedUpdateActuacion.mockResolvedValue({} as any);
  });

  it("PUT no reenvía LOCAL CERRADO stale tras merge y oficioCorrectionApplied", async () => {
    const staleDraft = baseOficioRow();
    const correctedRow: IActuacionListItem = {
      ...staleDraft,
      contraproducencia: null,
      realizo_nueva_inspeccion: false,
    };
    const rowForSubmit = mergeActuacionAfterOficioCorrection({
      correctedRow,
      pendingDraft: staleDraft,
    });

    expect(rowForSubmit.contraproducencia).toBeNull();

    await submitActuacionRow({
      id: 99,
      fullRow: rowForSubmit,
      oficioCorrectionApplied: true,
      skipValidation: false,
      skipUpdate: false,
    });

    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.contraproducencia).toBeUndefined();
  });

  it("circuito REINSPECCION_OFICIO omite contra aunque oficioCorrectionApplied sea false (Fix 2C.3)", async () => {
    const row = baseOficioRow();
    await submitActuacionRow({
      id: 99,
      fullRow: row,
      oficioCorrectionApplied: false,
      skipValidation: false,
      skipUpdate: false,
    });
    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.contraproducencia).toBeUndefined();
    expect(putBody.realizo_nueva_inspeccion).toBeUndefined();
    expect(putBody.limpiar_contraproducencia).toBeUndefined();
  });

  it("FIX.6.2 — PUT Oficio omite calle/rubro/contrib stale del payload", async () => {
    const row = {
      ...baseOficioRow(),
      calle: "",
      numero: "",
      rubro_nombre: "",
      doc_nro: "",
      contrib_apellido: "",
      contrib_nombre: "",
      can_edit_domicilio: false,
      can_edit_rubro: false,
    } as IActuacionListItem;
    await submitActuacionRow({
      id: 99,
      fullRow: row,
      skipValidation: true,
      skipUpdate: false,
    });
    const putBody = mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
    expect(putBody.calle).toBeUndefined();
    expect(putBody.numero).toBeUndefined();
    expect(putBody.rubro_nombre).toBeUndefined();
    expect(putBody.doc_nro).toBeUndefined();
    expect(putBody.contrib_apellido).toBeUndefined();
  });

  it("Ratificación CUMPLE tras clearingContra no exige acta inspección (FIX.4.1)", async () => {
    const original = baseOficioRow();
    const rowForSubmit = mergeActuacionAfterOficioCorrection({
      correctedRow: {
        ...original,
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        contraproducencia: null,
        resultado_cumplimiento_oficio: "CUMPLE",
        realizo_nueva_inspeccion: null,
      },
      pendingDraft: original,
    });

    const result = await submitActuacionRow({
      id: 99,
      fullRow: rowForSubmit,
      originalRow: original,
      oficioCorrectionApplied: true,
      oficioValidationContext: { subtipo: "RATIFICACION DE CLAUSURA", verificarEstadoOperativo: "" },
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(true);
    expect(mockedUpdateActuacion).toHaveBeenCalled();
  });

  it("Verificar SI → Clausura CUMPLE tras quitar actas no exige acta inspección (FIX.4.1)", async () => {
    const original = {
      ...baseOficioRow(),
      contraproducencia: null,
      realizo_nueva_inspeccion: true,
      acta_inspeccion_num: "000123",
    };
    const rowForSubmit = mergeActuacionAfterOficioCorrection({
      correctedRow: {
        ...original,
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        resultado_cumplimiento_oficio: "CUMPLE",
        realizo_nueva_inspeccion: null,
        acta_inspeccion_num: null,
      },
      pendingDraft: { ...original, acta_inspeccion_num: null },
    });

    const result = await submitActuacionRow({
      id: 99,
      fullRow: rowForSubmit,
      originalRow: original,
      oficioCorrectionApplied: true,
      actasClearedByOficioCorrection: ["INSPECCION"],
      oficioValidationContext: { subtipo: "RATIFICACION DE CLAUSURA", verificarEstadoOperativo: "" },
      skipValidation: false,
      skipUpdate: false,
    });

    expect(result.ok).toBe(true);
  });

  it("Clausura → Verificar SI sin acta bloquea validación (FIX.4.1)", async () => {
    const row = {
      ...baseOficioRow(),
      tipo_actuacion: "VERIFICAR E INFORMAR",
      contraproducencia: null,
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: true,
      acta_inspeccion_num: null,
      acta_comprobacion_num: null,
      calle: "",
      rubro_nombre: "",
      can_edit_domicilio: true,
    };

    const result = await submitActuacionRow({
      id: 99,
      fullRow: row,
      oficioValidationContext: { subtipo: "VERIFICAR E INFORMAR", verificarEstadoOperativo: "SI_INSPECCION" },
      skipValidation: false,
      skipUpdate: true,
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.kind).toBe("validation");
      expect(result.fieldErrors.acta_inspeccion_num).toBeTruthy();
      expect(result.fieldErrors.calle).toBeUndefined();
    }
    expect(mockedUpdateActuacion).not.toHaveBeenCalled();
  });

  it("FIX.6.1: Verificar SI → CONTRA tras quitar actas no exige calle ni acta", async () => {
    const original = {
      ...baseOficioRow(),
      contraproducencia: null,
      realizo_nueva_inspeccion: true,
      acta_inspeccion_num: "000123",
      acta_notificacion_num: "000456",
      calle: "",
      rubro_nombre: "",
      contrib_apellido: "",
      contrib_nombre: "",
      doc_nro: "",
      can_edit_domicilio: true,
    };
    const rowForSubmit = mergeActuacionAfterOficioCorrection({
      correctedRow: {
        ...original,
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: false,
        acta_inspeccion_num: null,
        acta_notificacion_num: null,
      },
      pendingDraft: {
        ...original,
        acta_inspeccion_num: null,
        acta_notificacion_num: null,
      },
    });

    const result = await submitActuacionRow({
      id: 99,
      fullRow: rowForSubmit,
      originalRow: original,
      oficioCorrectionApplied: true,
      actasClearedByOficioCorrection: ["INSPECCION", "NOTIFICACION"],
      oficioValidationContext: {
        subtipo: "VERIFICAR E INFORMAR",
        verificarEstadoOperativo: "CONTRAPRODUCENCIA",
      },
      skipValidation: false,
      skipUpdate: true,
    });

    expect(result.ok).toBe(true);
    if (!result.ok) {
      expect(result.fieldErrors.calle).toBeUndefined();
      expect(result.fieldErrors.acta_inspeccion_num).toBeUndefined();
    }
  });

  it("FIX.6.1: Verificar SI → NO tras quitar actas no exige calle ni acta", async () => {
    const original = {
      ...baseOficioRow(),
      contraproducencia: null,
      realizo_nueva_inspeccion: true,
      acta_inspeccion_num: "000123",
      calle: "",
      rubro_nombre: "",
      can_edit_domicilio: true,
    };
    const rowForSubmit = mergeActuacionAfterOficioCorrection({
      correctedRow: {
        ...original,
        contraproducencia: null,
        realizo_nueva_inspeccion: false,
        acta_inspeccion_num: null,
      },
      pendingDraft: { ...original, acta_inspeccion_num: null },
    });

    const result = await submitActuacionRow({
      id: 99,
      fullRow: rowForSubmit,
      originalRow: original,
      oficioCorrectionApplied: true,
      actasClearedByOficioCorrection: ["INSPECCION"],
      oficioValidationContext: {
        subtipo: "VERIFICAR E INFORMAR",
        verificarEstadoOperativo: "NO_INSPECCION",
      },
      skipValidation: false,
      skipUpdate: true,
    });

    expect(result.ok).toBe(true);
  });

  it("FIX.6.1: Verificar SI → Clausura CUMPLE pipeline sin calle ni acta", async () => {
    const original = {
      ...baseOficioRow(),
      contraproducencia: null,
      realizo_nueva_inspeccion: true,
      acta_inspeccion_num: "000123",
      calle: "",
      rubro_nombre: "",
      can_edit_domicilio: true,
    };
    const rowForSubmit = mergeActuacionAfterOficioCorrection({
      correctedRow: {
        ...original,
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        resultado_cumplimiento_oficio: "CUMPLE",
        realizo_nueva_inspeccion: null,
        acta_inspeccion_num: null,
      },
      pendingDraft: { ...original, acta_inspeccion_num: null },
    });

    const result = await submitActuacionRow({
      id: 99,
      fullRow: rowForSubmit,
      originalRow: original,
      oficioCorrectionApplied: true,
      actasClearedByOficioCorrection: ["INSPECCION"],
      oficioValidationContext: { subtipo: "RATIFICACION DE CLAUSURA", verificarEstadoOperativo: "" },
      skipValidation: false,
      skipUpdate: true,
    });

    expect(result.ok).toBe(true);
    if (!result.ok) {
      expect(result.fieldErrors.calle).toBeUndefined();
      expect(result.fieldErrors.acta_inspeccion_num).toBeUndefined();
    }
  });
});
