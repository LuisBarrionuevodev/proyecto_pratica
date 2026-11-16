import { describe, expect, it } from "vitest";
import {
  applyCompletarTrabajoFieldErrorsFromApi,
  isCompletarTrabajoCierreNoEnProcesoError,
} from "./completarTrabajoErrors";

describe("isCompletarTrabajoCierreNoEnProcesoError", () => {
  it("detecta mensaje ítem no EN_PROCESO (FINALIZADO)", () => {
    const err = {
      response: {
        status: 422,
        data: {
          detail: "El ítem no está EN_PROCESO (estado actual: FINALIZADO).",
        },
      },
    };
    expect(isCompletarTrabajoCierreNoEnProcesoError(err)).toBe(true);
  });

  it("no confunde otros 422", () => {
    const err = {
      response: {
        status: 422,
        data: { detail: "El acta de inspección es obligatoria." },
      },
    };
    expect(isCompletarTrabajoCierreNoEnProcesoError(err)).toBe(false);
  });
});

describe("applyCompletarTrabajoFieldErrorsFromApi documento ambiguo", () => {
  it("marca doc_nro, no informa éxito y deja el mensaje identificable", () => {
    const msg =
      "No pudimos identificar este documento con seguridad. Contactá a administración para revisarlo.";
    const result = applyCompletarTrabajoFieldErrorsFromApi({
      response: {
        status: 409,
        data: { detail: msg, codigo: "DOCUMENTO_AMBIGUO", errors: { doc_nro: msg } },
      },
    });
    expect(result.fieldErrors.doc_nro).toBe(msg);
    expect(result.severity).toBe("warning");
    expect(result.generalMessage).toBeTruthy();
  });
});
