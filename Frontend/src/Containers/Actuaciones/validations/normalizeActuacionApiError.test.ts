import { describe, expect, it } from "vitest";

import {
  ACTUACION_NETWORK_ERROR_MESSAGE,
  ACTUACION_FIELD_ERROR_SUMMARY,
  feedbackSeverityForActuacionError,
  mapActuacionApiFieldKey,
  mapActuacionNestedActaKey,
  normalizeActuacionApiError,
} from "./normalizeActuacionApiError";

describe("normalizeActuacionApiError", () => {
  it("422 + errors → validation con fieldErrors, sin Network Error", () => {
    const err = {
      response: {
        status: 422,
        data: {
          detail: "Validation error",
          errors: { comprobacion_motivo: "Motivo obligatorio" },
        },
      },
    };
    const n = normalizeActuacionApiError(err);
    expect(n.kind).toBe("validation");
    expect(n.status).toBe(422);
    expect(n.fieldErrors.comprobacion_motivo).toBe("Motivo obligatorio");
    expect(n.message).not.toBe("Network Error");
    expect(n.message).toBe(ACTUACION_FIELD_ERROR_SUMMARY);
  });

  it("400 detail → validation con mensaje humano", () => {
    const err = {
      response: {
        status: 400,
        data: { detail: "Acta ya asociada a otra actuación." },
      },
    };
    const n = normalizeActuacionApiError(err);
    expect(n.kind).toBe("validation");
    expect(n.message).toBe("Acta ya asociada a otra actuación.");
    expect(Object.keys(n.fieldErrors)).toHaveLength(0);
  });

  it("409 → conflict", () => {
    const err = {
      response: { status: 409, data: { detail: "Reingreso bloqueado" } },
    };
    const n = normalizeActuacionApiError(err);
    expect(n.kind).toBe("conflict");
    expect(feedbackSeverityForActuacionError(n.kind)).toBe("warning");
  });

  it("500 → server", () => {
    const err = {
      response: { status: 500, data: { detail: "Error interno" } },
    };
    const n = normalizeActuacionApiError(err);
    expect(n.kind).toBe("server");
    expect(feedbackSeverityForActuacionError(n.kind)).toBe("error");
  });

  it("sin response → network con mensaje controlado", () => {
    const err = new Error("Network Error");
    const n = normalizeActuacionApiError(err);
    expect(n.kind).toBe("network");
    expect(n.message).toBe(ACTUACION_NETWORK_ERROR_MESSAGE);
  });

  it("con response nunca devuelve Network Error literal", () => {
    const err = {
      message: "Network Error",
      response: { status: 400, data: { detail: "Rubro obligatorio" } },
    };
    const n = normalizeActuacionApiError(err);
    expect(n.message).not.toBe("Network Error");
    expect(n.fieldErrors.rubro_nombre).toBe("Rubro obligatorio");
  });
});

describe("mapActuacionNestedActaKey", () => {
  it("actas.comprobacion.* → acta_comprobacion_num", () => {
    expect(mapActuacionNestedActaKey("actas.comprobacion.numero")).toBe("acta_comprobacion_num");
  });

  it("actas.notificacion.* → acta_notificacion_num", () => {
    expect(mapActuacionNestedActaKey("actas.notificacion.num")).toBe("acta_notificacion_num");
  });

  it("actas.clausura.* → acta_clausura_num", () => {
    expect(mapActuacionNestedActaKey("actas.clausura.x")).toBe("acta_clausura_num");
  });

  it("actas.decomiso.* → acta_decomiso_num", () => {
    expect(mapActuacionNestedActaKey("actas.decomiso.x")).toBe("acta_decomiso_num");
  });

  it("actas.inspeccion.* → acta_inspeccion_num", () => {
    expect(mapActuacionNestedActaKey("actas.inspeccion.numero")).toBe("acta_inspeccion_num");
  });

  it("actas.0.numero ambiguo → _row", () => {
    expect(mapActuacionNestedActaKey("actas.0.numero")).toBe("_row");
  });
});

describe("mapActuacionApiFieldKey", () => {
  it("motivo ambiguo → _row", () => {
    expect(mapActuacionApiFieldKey("motivo")).toBe("_row");
  });

  it("alias comprobacion_exige_motivo_si_hay_acta", () => {
    expect(mapActuacionApiFieldKey("comprobacion_exige_motivo_si_hay_acta")).toBe("comprobacion_motivo");
  });
});
