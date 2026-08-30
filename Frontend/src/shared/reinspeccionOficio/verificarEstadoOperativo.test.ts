import { describe, expect, it } from "vitest";

import {
  deriveVerificarUiFromEstado,
  isPersistedVerificarOperationalInconsistent,
  resolveVerificarEstadoFromPersisted,
  verificarEstadoToPayload,
} from "./verificarEstadoOperativo";

describe("resolveVerificarEstadoFromPersisted", () => {
  it("contra + null → CONTRAPRODUCENCIA", () => {
    expect(
      resolveVerificarEstadoFromPersisted({
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: null,
      })
    ).toBe("CONTRAPRODUCENCIA");
  });

  it("null + false → NO_INSPECCION", () => {
    expect(
      resolveVerificarEstadoFromPersisted({
        contraproducencia: null,
        realizo_nueva_inspeccion: false,
      })
    ).toBe("NO_INSPECCION");
  });

  it("null + true → SI_INSPECCION", () => {
    expect(
      resolveVerificarEstadoFromPersisted({
        contraproducencia: null,
        realizo_nueva_inspeccion: true,
      })
    ).toBe("SI_INSPECCION");
  });

  it("contra + false → INCONSISTENTE", () => {
    expect(
      resolveVerificarEstadoFromPersisted({
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: false,
      })
    ).toBe("INCONSISTENTE");
  });

  it("contra + true → INCONSISTENTE", () => {
    expect(
      resolveVerificarEstadoFromPersisted({
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: true,
      })
    ).toBe("INCONSISTENTE");
  });

  it("null + null → vacío", () => {
    expect(resolveVerificarEstadoFromPersisted({})).toBe("");
  });
});

describe("deriveVerificarUiFromEstado", () => {
  it("Contra → No limpia contra", () => {
    const no = deriveVerificarUiFromEstado("NO_INSPECCION");
    expect(no.contraproducencia).toBe("");
    expect(no.realizoNuevaInspeccion).toBe("no");
  });

  it("Contra → Sí limpia contra", () => {
    const si = deriveVerificarUiFromEstado("SI_INSPECCION");
    expect(si.contraproducencia).toBe("");
    expect(si.realizoNuevaInspeccion).toBe("si");
  });

  it("No → Contra limpia realizo", () => {
    const contra = deriveVerificarUiFromEstado("CONTRAPRODUCENCIA", "LOCAL CERRADO");
    expect(contra.realizoNuevaInspeccion).toBe("");
    expect(contra.contraproducencia).toBe("LOCAL CERRADO");
  });
});

describe("verificarEstadoToPayload", () => {
  const tipo = "VERIFICAR E INFORMAR";

  it("CONTRAPRODUCENCIA", () => {
    expect(
      verificarEstadoToPayload({
        tipoActuacion: tipo,
        verificarEstado: "CONTRAPRODUCENCIA",
        contraproducencia: "LOCAL CERRADO",
      })
    ).toEqual({
      tipo_actuacion: tipo,
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: null,
      contraproducencia: "LOCAL CERRADO",
    });
  });

  it("NO_INSPECCION", () => {
    expect(
      verificarEstadoToPayload({
        tipoActuacion: tipo,
        verificarEstado: "NO_INSPECCION",
        contraproducencia: "LOCAL CERRADO",
      })
    ).toEqual({
      tipo_actuacion: tipo,
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: false,
      contraproducencia: null,
    });
  });

  it("SI_INSPECCION", () => {
    expect(
      verificarEstadoToPayload({
        tipoActuacion: tipo,
        verificarEstado: "SI_INSPECCION",
        contraproducencia: "LOCAL CERRADO",
      })
    ).toEqual({
      tipo_actuacion: tipo,
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: true,
      contraproducencia: null,
    });
  });
});

describe("isPersistedVerificarOperationalInconsistent", () => {
  it("detecta híbrido", () => {
    expect(
      isPersistedVerificarOperationalInconsistent({
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: true,
      })
    ).toBe(true);
  });
});
