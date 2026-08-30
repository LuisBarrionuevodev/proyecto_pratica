import { describe, expect, it } from "vitest";

import {
  MSG_SI_A_NO_CON_ACTAS,
  MSG_RESULTADO_REQUERIDO,
  MSG_VERIFICAR_ESTADO_REQUERIDO,
  isPersistedOficioOperationalInconsistent,
  isPersistedVerificarOperationalInconsistent,
  oficioCorreccionDirty,
  oficioCorreccionPayloadFromUi,
  validateReinspeccionOficioForm,
} from "./reinspeccionOficioValidation";

describe("validateReinspeccionOficioForm", () => {
  it("exige cumplimiento en ratificación", () => {
    const r = validateReinspeccionOficioForm({
      esRatificacion: true,
      esVerificar: false,
      cumplimientoUi: "",
      contraproducencia: "",
      realizoNuevaInspeccion: "",
      tieneActasInspeccionNormal: false,
    });
    expect(r).toEqual({ ok: false, field: "resultado_cumplimiento_oficio", message: MSG_RESULTADO_REQUERIDO });
  });

  it("exige contraproducencia cuando UI es CONTRAPRODUCENCIA", () => {
    const r = validateReinspeccionOficioForm({
      esRatificacion: true,
      esVerificar: false,
      cumplimientoUi: "CONTRAPRODUCENCIA",
      contraproducencia: "",
      realizoNuevaInspeccion: "",
      tieneActasInspeccionNormal: false,
    });
    expect(r.ok).toBe(false);
  });

  it("exige estado operativo en verificar", () => {
    const r = validateReinspeccionOficioForm({
      esRatificacion: false,
      esVerificar: true,
      cumplimientoUi: "",
      contraproducencia: "",
      realizoNuevaInspeccion: "",
      verificarEstadoOperativo: "",
      tieneActasInspeccionNormal: false,
    });
    expect(r).toEqual({
      ok: false,
      field: "verificar_estado_operativo",
      message: MSG_VERIFICAR_ESTADO_REQUERIDO,
    });
  });

  it("bloquea Sí→No con actas", () => {
    const r = validateReinspeccionOficioForm({
      esRatificacion: false,
      esVerificar: true,
      cumplimientoUi: "",
      contraproducencia: "",
      realizoNuevaInspeccion: "no",
      verificarEstadoOperativo: "NO_INSPECCION",
      tieneActasInspeccionNormal: true,
    });
    expect(r).toEqual({
      ok: false,
      field: "verificar_estado_operativo",
      message: MSG_SI_A_NO_CON_ACTAS,
    });
  });
});

describe("oficioCorreccionDirty", () => {
  it("detecta cambio de subtipo", () => {
    const dirty = oficioCorreccionDirty(
      { tipo_actuacion: "RATIFICACION DE CLAUSURA", resultado_cumplimiento_oficio: "CUMPLE" },
      {
        tipoActuacion: "VERIFICAR E INFORMAR",
        cumplimientoUi: "",
        contraproducencia: "",
        realizoNuevaInspeccion: "no",
        verificarEstadoOperativo: "NO_INSPECCION",
      }
    );
    expect(dirty).toBe(true);
  });

  it("detecta cambio contra→CUMPLE", () => {
    const dirty = oficioCorreccionDirty(
      { resultado_cumplimiento_oficio: null, contraproducencia: "NO SE RATIFICÓ" },
      { cumplimientoUi: "CUMPLE", contraproducencia: "", realizoNuevaInspeccion: "" }
    );
    expect(dirty).toBe(true);
  });

  it("sin cambios retorna false", () => {
    const dirty = oficioCorreccionDirty(
      { resultado_cumplimiento_oficio: "CUMPLE", contraproducencia: null },
      { cumplimientoUi: "CUMPLE", contraproducencia: "", realizoNuevaInspeccion: "" }
    );
    expect(dirty).toBe(false);
  });

  it("detecta estado persistido inconsistente CUMPLE + contra (Fix 2C.3)", () => {
    expect(
      isPersistedOficioOperationalInconsistent({
        resultado_cumplimiento_oficio: "CUMPLE",
        contraproducencia: "LOCAL CERRADO",
      })
    ).toBe(true);

    const dirty = oficioCorreccionDirty(
      { resultado_cumplimiento_oficio: "CUMPLE", contraproducencia: "LOCAL CERRADO" },
      { cumplimientoUi: "CUMPLE", contraproducencia: "LOCAL CERRADO", realizoNuevaInspeccion: "" }
    );
    expect(dirty).toBe(true);
  });

  it("tras reparación consistente dirty es false", () => {
    const dirty = oficioCorreccionDirty(
      { resultado_cumplimiento_oficio: "CUMPLE", contraproducencia: null },
      { cumplimientoUi: "CUMPLE", contraproducencia: "", realizoNuevaInspeccion: "" }
    );
    expect(dirty).toBe(false);
  });
});

describe("oficioCorreccionPayloadFromUi", () => {
  it("CUMPLE normaliza contraproducencia a null aunque oficioContra residual", () => {
    const payload = oficioCorreccionPayloadFromUi({
      tipoActuacion: "RATIFICACION DE CLAUSURA",
      cumplimientoUi: "CUMPLE",
      contraproducencia: "LOCAL CERRADO",
      realizoNuevaInspeccion: "",
      esRatificacion: true,
      esVerificar: false,
    });
    expect(payload).toEqual({
      tipo_actuacion: "RATIFICACION DE CLAUSURA",
      resultado_cumplimiento_oficio: "CUMPLE",
      contraproducencia: null,
    });
  });

  it("Verificar CONTRAPRODUCENCIA nunca híbrido", () => {
    const payload = oficioCorreccionPayloadFromUi({
      tipoActuacion: "VERIFICAR E INFORMAR",
      cumplimientoUi: "",
      contraproducencia: "LOCAL CERRADO",
      realizoNuevaInspeccion: "si",
      verificarEstadoOperativo: "CONTRAPRODUCENCIA",
      esRatificacion: false,
      esVerificar: true,
    });
    expect(payload).toEqual({
      tipo_actuacion: "VERIFICAR E INFORMAR",
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: null,
      contraproducencia: "LOCAL CERRADO",
    });
  });

  it("Verificar NO_INSPECCION limpia contra", () => {
    const payload = oficioCorreccionPayloadFromUi({
      tipoActuacion: "VERIFICAR E INFORMAR",
      cumplimientoUi: "",
      contraproducencia: "LOCAL CERRADO",
      realizoNuevaInspeccion: "no",
      verificarEstadoOperativo: "NO_INSPECCION",
      esRatificacion: false,
      esVerificar: true,
    });
    expect(payload).toEqual({
      tipo_actuacion: "VERIFICAR E INFORMAR",
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: false,
      contraproducencia: null,
    });
  });
});

describe("oficioCorreccionDirty verificar", () => {
  it("Contra → No es dirty", () => {
    expect(
      oficioCorreccionDirty(
        { contraproducencia: "LOCAL CERRADO", realizo_nueva_inspeccion: null },
        {
          cumplimientoUi: "",
          contraproducencia: "",
          realizoNuevaInspeccion: "no",
          verificarEstadoOperativo: "NO_INSPECCION",
        }
      )
    ).toBe(true);
  });

  it("híbrido persistido siempre dirty", () => {
    expect(
      isPersistedVerificarOperationalInconsistent({
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: true,
      })
    ).toBe(true);
    expect(
      oficioCorreccionDirty(
        { contraproducencia: "LOCAL CERRADO", realizo_nueva_inspeccion: true },
        {
          cumplimientoUi: "",
          contraproducencia: "LOCAL CERRADO",
          realizoNuevaInspeccion: "si",
          verificarEstadoOperativo: "CONTRAPRODUCENCIA",
        }
      )
    ).toBe(true);
  });
});
