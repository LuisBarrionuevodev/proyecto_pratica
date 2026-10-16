import { describe, expect, it } from "vitest";
import { isCompletarTrabajoCierreNoEnProcesoError } from "./completarTrabajoErrors";

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
