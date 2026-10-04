import { describe, expect, it } from "vitest";
import { MEDIA_RUTA_ITEM_GALLERIES } from "./mediaConstants";
import { runCompletarTrabajoFinalizeFlow } from "../../Containers/CompletarTrabajos/utils/completarTrabajoFinalizeFlow";
import { vi } from "vitest";

describe("MEDIA.1B configuración galerías", () => {
  it("expone tres galerías en orden doc / actas / inspección", () => {
    expect(MEDIA_RUTA_ITEM_GALLERIES).toHaveLength(3);
    expect(MEDIA_RUTA_ITEM_GALLERIES[0].cupo).toBe(9);
    expect(MEDIA_RUTA_ITEM_GALLERIES[1].cupo).toBe(7);
    expect(MEDIA_RUTA_ITEM_GALLERIES[2].cupo).toBe(12);
    expect(MEDIA_RUTA_ITEM_GALLERIES[2].categoria).toBe("FOTO_INSPECCION");
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
