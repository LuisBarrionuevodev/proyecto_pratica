import { describe, expect, it } from "vitest";
import { MEDIA_1A_GALLERIES } from "./mediaConstants";
import { runCompletarTrabajoFinalizeFlow } from "../../Containers/CompletarTrabajos/utils/completarTrabajoFinalizeFlow";
import { vi } from "vitest";

describe("MEDIA.1A.3 configuración galerías", () => {
  it("expone cupos 9 y 7 sin FOTO_INSPECCION", () => {
    expect(MEDIA_1A_GALLERIES).toHaveLength(2);
    expect(MEDIA_1A_GALLERIES[0].cupo).toBe(9);
    expect(MEDIA_1A_GALLERIES[1].cupo).toBe(7);
    expect(MEDIA_1A_GALLERIES.some((g) => g.categoria === "FOTO_INSPECCION")).toBe(false);
  });
});

describe("flujo global de carga", () => {
  it("una sola pasada de upload para varias categorías", async () => {
    const upload = vi.fn().mockResolvedValue(true);
    const cierre = vi.fn();
    await runCompletarTrabajoFinalizeFlow({
      validate: () => ({ canSubmit: true, fieldErrors: {} }),
      uploadPendingMedia: upload,
      submitCierre: cierre,
    });
    expect(upload).toHaveBeenCalledTimes(1);
    expect(cierre).toHaveBeenCalledTimes(1);
  });
});
