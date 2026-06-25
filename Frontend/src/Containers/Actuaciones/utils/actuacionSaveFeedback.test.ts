import { describe, expect, it, vi } from "vitest";

import type { AppFeedback } from "../../../components/feedback/GlobalFeedbackProvider";
import {
  buildActuacionSaveFeedbackMessage,
  MENSAJE_ERROR_GRAVE,
  MENSAJE_GUARDADO_OK,
  MENSAJE_VALIDACION_LOCAL,
  notifyActuacionSaveResult,
} from "./actuacionSaveFeedback";
import type { SubmitActuacionRowResult } from "./submitActuacionRow";

function mockFeedback(): AppFeedback {
  return {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  };
}

describe("buildActuacionSaveFeedbackMessage", () => {
  it("éxito → success azul", () => {
    expect(buildActuacionSaveFeedbackMessage({ ok: true })).toEqual({
      severity: "success",
      message: MENSAJE_GUARDADO_OK,
    });
  });

  it("validación con campos → warning con lista de labels", () => {
    const result: SubmitActuacionRowResult = {
      ok: false,
      kind: "validation",
      fieldErrors: { calle: "Calle requerida", rubro_nombre: "Rubro requerido" },
    };
    expect(buildActuacionSaveFeedbackMessage(result)).toEqual({
      severity: "warning",
      message: "Revisá: Calle, Rubro.",
    });
  });

  it("prioriza globalMessage con Revisá: si viene del helper", () => {
    const result: SubmitActuacionRowResult = {
      ok: false,
      kind: "validation",
      fieldErrors: { calle: "Calle requerida" },
      globalMessage: "Revisá: Calle, Rubro.",
    };
    expect(buildActuacionSaveFeedbackMessage(result)?.message).toBe("Revisá: Calle, Rubro.");
    expect(buildActuacionSaveFeedbackMessage(result)?.severity).toBe("warning");
  });

  it("error grave → error rojo", () => {
    expect(
      buildActuacionSaveFeedbackMessage({ ok: false, kind: "generic", message: "Timeout" })
    ).toEqual({ severity: "error", message: "Timeout" });
    expect(
      buildActuacionSaveFeedbackMessage({ ok: false, kind: "generic", message: "" })
    ).toEqual({ severity: "error", message: MENSAJE_ERROR_GRAVE });
  });

  it("sin campos ni global usa mensaje local estándar", () => {
    const result: SubmitActuacionRowResult = {
      ok: false,
      kind: "validation",
      fieldErrors: {},
    };
    expect(buildActuacionSaveFeedbackMessage(result)?.message).toBe(MENSAJE_VALIDACION_LOCAL);
  });
});

describe("notifyActuacionSaveResult", () => {
  it("validación local dispara warning, no error", () => {
    const feedback = mockFeedback();
    notifyActuacionSaveResult(
      {
        ok: false,
        kind: "validation",
        fieldErrors: { comprobacion_motivo: "Obligatorio" },
      },
      feedback
    );
    expect(feedback.warning).toHaveBeenCalledWith("Revisá: Motivo de comprobación.");
    expect(feedback.error).not.toHaveBeenCalled();
  });

  it("guardado correcto usa feedback success", () => {
    const feedback = mockFeedback();
    notifyActuacionSaveResult({ ok: true }, feedback);
    expect(feedback.success).toHaveBeenCalledWith(MENSAJE_GUARDADO_OK);
  });

  it("error grave usa feedback error", () => {
    const feedback = mockFeedback();
    notifyActuacionSaveResult({ ok: false, kind: "generic", message: "Error de servidor" }, feedback);
    expect(feedback.error).toHaveBeenCalledWith("Error de servidor");
  });
});
