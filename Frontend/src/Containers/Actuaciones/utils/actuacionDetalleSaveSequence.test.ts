import { describe, expect, it, vi } from "vitest";
import { runEditActuacionSaveFlow } from "./actuacionEditSaveSession";

describe("actuacionDetalleSaveSequence HOTFIX V1.1-CRUD-ACTUACIONES.1 / ROBUSTEZ.1", () => {
  it("PUT fallido no sube fotos ni cierra", async () => {
    const uploadPhotos = vi.fn(async () => "success" as const);
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => true,
      putSave: async () => false,
      uploadPhotos,
    });
    expect(uploadPhotos).not.toHaveBeenCalled();
    expect(result.sessionOutcome).toBe("aborted");
    expect(result.awaitingPhotos).toBe(false);
  });

  it("PUT exitoso con cola sube fotos y luego cierra sesión una vez", async () => {
    const order: string[] = [];
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => true,
      putSave: async () => {
        order.push("put");
        return true;
      },
      uploadPhotos: async () => {
        order.push("upload");
        return "success";
      },
    });
    expect(order).toEqual(["put", "upload"]);
    expect(result.sessionOutcome).toBe("success");
  });

  it("subida parcial aborta sesión sin cierre exitoso", async () => {
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => true,
      putSave: async () => true,
      uploadPhotos: async () => "partial",
    });
    expect(result.sessionOutcome).toBe("aborted");
    expect(result.awaitingPhotos).toBe(true);
  });

  it("reintento tras PUT confirmado no vuelve a guardar datos", async () => {
    const putSave = vi.fn(async () => true);
    await runEditActuacionSaveFlow({
      datosYaConfirmados: true,
      fotosIncompletas: () => true,
      putSave,
      uploadPhotos: async () => "partial",
    });
    expect(putSave).not.toHaveBeenCalled();
  });
});
