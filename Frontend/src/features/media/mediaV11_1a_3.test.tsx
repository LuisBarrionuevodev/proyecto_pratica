import { describe, expect, it } from "vitest";
import { MEDIA_CATEGORY_CONFIG_1A } from "./mediaConstants";
import { runCompletarTrabajoFinalizeFlow } from "../../Containers/CompletarTrabajos/utils/completarTrabajoFinalizeFlow";
import { vi } from "vitest";

describe("MEDIA.1A.3 configuración galerías", () => {
  it("expone cupos 9 y 7 sin FOTO_INSPECCION", () => {
    expect(MEDIA_CATEGORY_CONFIG_1A.FOTO_DOCUMENTACION_LOCAL.cupo).toBe(9);
    expect(MEDIA_CATEGORY_CONFIG_1A.FOTO_ACTA.cupo).toBe(7);
    expect("FOTO_INSPECCION" in MEDIA_CATEGORY_CONFIG_1A).toBe(false);
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
