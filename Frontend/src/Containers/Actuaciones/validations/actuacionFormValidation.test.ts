import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { CONTRAPRODUCCION_NO_PERMITE_INSPECCION, CORRECTIVA_NO_ES_EL_RUBRO } from "../../CompletarTrabajos/utils/completarTrabajoContraproducencia";
import {
  ACTUACION_VALIDATION_MESSAGES,
  actuacionCompletarTrabajoValidationContext,
  actuacionCrudValidationContext,
  validateActuacionFormForSubmit,
} from "./actuacionFormValidation";
import {
  normalizeActuacionRowForCrudSubmit,
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

describe("validateActuacionFormForSubmit — CRUD Editar Actuación", () => {
  it("form válido permite submit", () => {
    const result = validateActuacionFormForSubmit(baseRow, actuacionCrudValidationContext(baseRow));
    expect(result.canSubmit).toBe(true);
  });

  it("PR7.15d: domicilio bloqueado no exige calle ni rubro aunque estén vacíos", () => {
    const row = {
      ...baseRow,
      can_edit_domicilio: false,
      domicilio_edit_blocked_reason:
        "El domicilio no puede modificarse porque el acta ya fue utilizada en un circuito posterior.",
      calle: "",
      numero: "",
      rubro_nombre: "",
    };
    const result = validateActuacionFormForSubmit(row, actuacionCrudValidationContext(row));
    expect(result.fieldErrors.calle).toBeUndefined();
    expect(result.fieldErrors.rubro_nombre).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("ratificación no bloquea por nombre/documento faltante", () => {
    const row = {
      ...baseRow,
      tipo_actuacion: "RATIFICACION DE CLAUSURA",
      contrib_apellido: "",
      contrib_nombre: "",
      doc_nro: "",
    };
    const result = validateActuacionFormForSubmit(row, actuacionCrudValidationContext(row));
    expect(result.fieldErrors.contrib_apellido).toBeUndefined();
    expect(result.fieldErrors.doc_nro).toBeUndefined();
  });

  it("reinspección por notificación no exige notificación nueva", () => {
    const row = {
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      acta_notificacion_num: "",
      notificacion_motivo_1: null,
      contrib_apellido: "",
      doc_nro: "",
    };
    const result = validateActuacionFormForSubmit(row, actuacionCrudValidationContext(row));
    expect(result.fieldErrors.notificacion_motivo_1).toBeUndefined();
    expect(result.fieldErrors.contrib_apellido).toBeUndefined();
  });

  it("bloquea si no hay nombre/apellido ni razón social", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, contrib_apellido: "", contrib_nombre: "", razon_social: null },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.contrib_apellido).toBe(ACTUACION_VALIDATION_MESSAGES.titularRequerido);
  });

  it("permite razón social sin nombre/apellido", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, contrib_apellido: null, contrib_nombre: null, razon_social: "ACME SA" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.contrib_apellido).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("bloquea documento/CUIT con menos de 7 dígitos", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, doc_nro: "345678" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.doc_nro).toContain("al menos 7");
  });

  it("permite documento de 7 dígitos", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, doc_nro: "1234567" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.doc_nro).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("rechaza CUIT con guiones", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, doc_nro: "20-34567890-1" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.doc_nro).toBeTruthy();
  });

  it("nombre de fantasía vacío permite guardar", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, nombre_local: null },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.canSubmit).toBe(true);
  });

  it("acta 25 es válida (se normaliza después)", () => {
    const parsed = validateAndNormalizeActaNum("25");
    expect(parsed.ok).toBe(true);
    if (parsed.ok) expect(parsed.normalized).toBe("000025");
  });

  it("acta con más de 6 dígitos bloquea", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, acta_inspeccion_num: "1234567" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.acta_inspeccion_num).toBeTruthy();
  });

  it("acta con letras bloquea", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, acta_inspeccion_num: "ABC123" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.acta_inspeccion_num).toBeTruthy();
  });

  it("notificación sin inspección bloquea", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...baseRow,
        acta_inspeccion_num: "",
        acta_notificacion_num: "000100",
        notificacion_motivo_1: "Motivo A",
      },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.acta_inspeccion_num).toBe(
      ACTUACION_VALIDATION_MESSAGES.notificacionRequiereInspeccion
    );
  });

  it("comprobación sin inspección permite guardar", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...baseRow,
        acta_inspeccion_num: "",
        acta_comprobacion_num: "000200",
        comprobacion_motivo: "Incumplimiento",
      },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.acta_inspeccion_num).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("clausura/decomiso vacíos no bloquean", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, acta_clausura_num: null, acta_decomiso_num: null },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.canSubmit).toBe(true);
  });

  it("menos de 2 inspectores bloquea", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, inspector2: null, inspectores: ["García"] },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.inspectores).toBe(ACTUACION_VALIDATION_MESSAGES.inspectoresMinimoDos);
  });

  it("comprobación sin motivo bloquea si hay acta", () => {
    const result = validateActuacionFormForSubmit(
      { ...baseRow, acta_comprobacion_num: "900", comprobacion_motivo: "" },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.comprobacion_motivo).toBeTruthy();
  });

  it("notificación sin motivos bloquea si hay acta", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...baseRow,
        acta_notificacion_num: "800",
        acta_inspeccion_num: "100",
        notificacion_motivo_1: null,
      },
      actuacionCrudValidationContext(baseRow)
    );
    expect(result.fieldErrors.notificacion_motivo_1).toBeTruthy();
  });

  it("actuación normal no exige oficio", () => {
    const result = validateActuacionFormForSubmit(baseRow, actuacionCrudValidationContext(baseRow));
    expect(result.fieldErrors.oficio_numero).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("no valida notificación bloqueada por expediente", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...baseRow,
        notificacion_editable: false,
        acta_notificacion_num: "800",
        notificacion_motivo_1: null,
      },
      actuacionCrudValidationContext({ ...baseRow, notificacion_editable: false })
    );
    expect(result.canSubmit).toBe(true);
  });
});

describe("normalizeActuacionRowForCrudSubmit", () => {
  it("normaliza acta 25 a 000025 en fila", () => {
    const normalized = normalizeActuacionRowForCrudSubmit({ ...baseRow, acta_inspeccion_num: "25" });
    expect(normalized.acta_inspeccion_num).toBe("000025");
  });
});

describe("validateDocNro", () => {
  it("acepta 7 dígitos", () => {
    expect(validateDocNro("1234567")).toBeNull();
  });

  it("acepta 11 dígitos", () => {
    expect(validateDocNro("20345678901")).toBeNull();
  });

  it("rechaza guiones", () => {
    expect(validateDocNro("20-34567890-1")).toBeTruthy();
  });
});

describe("validateActuacionFormForSubmit — Completar trabajo", () => {
  const ctx = () => actuacionCompletarTrabajoValidationContext(true, false);
  const ctxVisitaNo = () => actuacionCompletarTrabajoValidationContext(false, false);

  const visitaRealizadaForm = {
    contraproducencia: "",
    calle: "San Martín",
    numero: "100",
    rubro_nombre: "Bar",
    doc_nro: "1234567",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    razon_social: null as string | null,
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
    inspector1: "García",
    inspector2: "López",
    inspector3: null,
    inspectores: ["García", "López"],
  };

  it("contexto incluye reglas de completar trabajo", () => {
    const c = actuacionCompletarTrabajoValidationContext(true, false);
    expect(c.source).toBe("completarTrabajo");
    expect(c.includeCompletarTrabajoRules).toBe(true);
    expect(c.includeCrudEditRules).toBe(false);
    expect(c.includeSharedFormRules).toBe(true);
  });

  it("contraproducencia genérica no exige actas ni titular", () => {
    const result = validateActuacionFormForSubmit(
      {
        contraproducencia: "LOCAL CERRADO",
        acta_inspeccion_num: "",
        acta_comprobacion_num: "",
        doc_nro: "",
        contrib_apellido: "",
        contrib_nombre: "",
        rubro_nombre: "Bar",
      },
      ctxVisitaNo()
    );
    expect(result.fieldErrors.acta_inspeccion_num).toBeUndefined();
    expect(result.fieldErrors.contrib_apellido).toBeUndefined();
    expect(result.fieldErrors.doc_nro).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("NO ES EL RUBRO exige rubro corregido", () => {
    const result = validateActuacionFormForSubmit(
      { contraproducencia: CORRECTIVA_NO_ES_EL_RUBRO, rubro_nombre: "" },
      ctxVisitaNo()
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.rubro_nombre).toBe(ACTUACION_VALIDATION_MESSAGES.rubroCorrectiva);
  });

  it("visita realizada sin actas bloquea", () => {
    const result = validateActuacionFormForSubmit(
      { ...visitaRealizadaForm, acta_inspeccion_num: "", acta_comprobacion_num: "" },
      ctx()
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.acta_inspeccion_num).toBe(
      ACTUACION_VALIDATION_MESSAGES.actaInspeccionOComprobacionRequerida
    );
  });

  it("visita realizada con solo acta de inspección permite", () => {
    const result = validateActuacionFormForSubmit(
      { ...visitaRealizadaForm, acta_inspeccion_num: "42", acta_comprobacion_num: "" },
      ctx()
    );
    expect(result.fieldErrors.acta_inspeccion_num).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("visita realizada con solo acta de comprobación permite", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...visitaRealizadaForm,
        acta_inspeccion_num: "",
        acta_comprobacion_num: "200",
        comprobacion_motivo: "Incumplimiento",
      },
      ctx()
    );
    expect(result.fieldErrors.acta_inspeccion_num).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });

  it("visita realizada exige titular y documento mínimo 7 dígitos", () => {
    const result = validateActuacionFormForSubmit(
      { ...visitaRealizadaForm, doc_nro: "123456", contrib_apellido: "", contrib_nombre: "" },
      ctx()
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.doc_nro).toBeTruthy();
    expect(result.fieldErrors.contrib_apellido).toBeTruthy();
  });

  it("visita realizada exige mínimo 2 inspectores", () => {
    const result = validateActuacionFormForSubmit(
      { ...visitaRealizadaForm, inspector2: null, inspectores: ["García"] },
      ctx()
    );
    expect(result.fieldErrors.inspectores).toBe(ACTUACION_VALIDATION_MESSAGES.inspectoresMinimoDos);
  });

  it("notificación sin inspección bloquea en completar trabajo", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...visitaRealizadaForm,
        acta_inspeccion_num: "",
        acta_notificacion_num: "000100",
        notificacion_motivo_1: "Motivo A",
      },
      ctx()
    );
    expect(result.fieldErrors.acta_inspeccion_num).toBe(
      ACTUACION_VALIDATION_MESSAGES.notificacionRequiereInspeccion
    );
  });

  it("notificación con inspección y motivo permite", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...visitaRealizadaForm,
        acta_inspeccion_num: "100",
        acta_notificacion_num: "200",
        notificacion_motivo_1: "Motivo A",
      },
      ctx()
    );
    expect(result.canSubmit).toBe(true);
  });

  it("notificación sin motivo bloquea", () => {
    const result = validateActuacionFormForSubmit(
      {
        ...visitaRealizadaForm,
        acta_notificacion_num: "800",
        notificacion_motivo_1: null,
      },
      ctx()
    );
    expect(result.fieldErrors.notificacion_motivo_1).toBeTruthy();
  });

  it("NO PERMITE INSPECCIÓN exige acta de comprobación y motivo", () => {
    const result = validateActuacionFormForSubmit(
      {
        contraproducencia: CONTRAPRODUCCION_NO_PERMITE_INSPECCION,
        acta_comprobacion_num: "",
        comprobacion_motivo: "",
      },
      ctxVisitaNo()
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.acta_comprobacion_num).toBe(
      ACTUACION_VALIDATION_MESSAGES.comprobacionNoPermiteInspeccion
    );
    expect(result.fieldErrors.comprobacion_motivo).toBe(
      ACTUACION_VALIDATION_MESSAGES.comprobacionNoPermiteInspeccion
    );
  });

  it("NO PERMITE INSPECCIÓN no exige titular ni documento", () => {
    const result = validateActuacionFormForSubmit(
      {
        contraproducencia: CONTRAPRODUCCION_NO_PERMITE_INSPECCION,
        acta_comprobacion_num: "100",
        comprobacion_motivo: "Motivo",
        doc_nro: "",
        contrib_apellido: "",
      },
      ctxVisitaNo()
    );
    expect(result.fieldErrors.doc_nro).toBeUndefined();
    expect(result.fieldErrors.contrib_apellido).toBeUndefined();
    expect(result.canSubmit).toBe(true);
  });
});
