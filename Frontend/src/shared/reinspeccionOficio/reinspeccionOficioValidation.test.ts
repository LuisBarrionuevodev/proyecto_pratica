import { describe, expect, it } from "vitest";

import {
  MSG_REALIZO_REQUERIDO,
  MSG_RESULTADO_REQUERIDO,
  MSG_SI_A_NO_CON_ACTAS,
  oficioCorreccionDirty,
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

  it("exige realizo en verificar", () => {
    const r = validateReinspeccionOficioForm({
      esRatificacion: false,
      esVerificar: true,
      cumplimientoUi: "",
      contraproducencia: "",
      realizoNuevaInspeccion: "",
      tieneActasInspeccionNormal: false,
    });
    expect(r).toEqual({ ok: false, field: "realizo_nueva_inspeccion", message: MSG_REALIZO_REQUERIDO });
  });

  it("bloquea Sí→No con actas", () => {
    const r = validateReinspeccionOficioForm({
      esRatificacion: false,
      esVerificar: true,
      cumplimientoUi: "",
      contraproducencia: "",
      realizoNuevaInspeccion: "no",
      tieneActasInspeccionNormal: true,
    });
    expect(r).toEqual({ ok: false, field: "realizo_nueva_inspeccion", message: MSG_SI_A_NO_CON_ACTAS });
  });
});

describe("oficioCorreccionDirty", () => {
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
});
