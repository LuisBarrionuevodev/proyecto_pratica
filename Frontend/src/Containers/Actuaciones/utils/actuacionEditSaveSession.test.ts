import { describe, expect, it, vi } from "vitest";
import {
  EDIT_CONTINUAR_SUBIDA_LABEL,
  EDIT_GUARDAR_CAMBIOS_LABEL,
  MENSAJE_EDIT_DATOS_OK_FOTOS_PENDIENTES,
  MENSAJE_EDIT_DATOS_INCERTOS,
  MENSAJE_EDIT_FOTOS_CIERRE_SIN_RECUPERAR,
  editSavePrimaryLabel,
  resolveEditSavePrimaryAction,
  runEditActuacionSaveFlow,
  shouldCloseEditModalAfterMedia,
} from "./actuacionEditSaveSession";

describe("actuacionEditSaveSession", () => {
  it("éxito de datos y fotos: PUT una vez, sube y cierra", async () => {
    const putSave = vi.fn(async () => true);
    const uploadPhotos = vi.fn(async () => "success" as const);
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => true,
      putSave,
      uploadPhotos,
    });
    expect(putSave).toHaveBeenCalledOnce();
    expect(uploadPhotos).toHaveBeenCalledOnce();
    expect(result).toEqual({
      didPut: true,
      didUpload: true,
      sessionOutcome: "success",
      awaitingPhotos: false,
    });
  });

  it("PUT confirmado y fallo antes de intent: modal abierto, Continuar subida", async () => {
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => true,
      putSave: async () => true,
      uploadPhotos: async () => "partial",
    });
    expect(result.didPut).toBe(true);
    expect(result.awaitingPhotos).toBe(true);
    expect(result.sessionOutcome).toBe("aborted");
    expect(resolveEditSavePrimaryAction(true)).toBe("continue_photos");
    expect(editSavePrimaryLabel("continue_photos")).toBe(EDIT_CONTINUAR_SUBIDA_LABEL);
    expect(MENSAJE_EDIT_DATOS_OK_FOTOS_PENDIENTES).toMatch(/se guardó/i);
  });

  it("reintento con datos ya confirmados no llama PUT", async () => {
    const putSave = vi.fn(async () => true);
    const uploadPhotos = vi.fn(async () => "success" as const);
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: true,
      fotosIncompletas: () => true,
      putSave,
      uploadPhotos,
    });
    expect(putSave).not.toHaveBeenCalled();
    expect(uploadPhotos).toHaveBeenCalledOnce();
    expect(result.didPut).toBe(false);
    expect(result.sessionOutcome).toBe("success");
  });

  it("varias fotos: éxito solo si uploadPhotos reporta success", async () => {
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: true,
      fotosIncompletas: () => true,
      putSave: async () => true,
      uploadPhotos: async () => "partial",
    });
    expect(result.sessionOutcome).toBe("aborted");
    expect(shouldCloseEditModalAfterMedia("partial")).toBe(false);
    expect(shouldCloseEditModalAfterMedia("empty")).toBe(false);
    expect(shouldCloseEditModalAfterMedia("success")).toBe(true);
  });

  it("sin fotos incompletas no sube y cierra como éxito", async () => {
    const uploadPhotos = vi.fn(async () => "success" as const);
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => false,
      putSave: async () => true,
      uploadPhotos,
    });
    expect(uploadPhotos).not.toHaveBeenCalled();
    expect(result.sessionOutcome).toBe("success");
    expect(editSavePrimaryLabel("save_data")).toBe(EDIT_GUARDAR_CAMBIOS_LABEL);
  });

  it("PUT fallido no sube fotos ni afirma guardado", async () => {
    const uploadPhotos = vi.fn();
    const result = await runEditActuacionSaveFlow({
      datosYaConfirmados: false,
      fotosIncompletas: () => true,
      putSave: async () => false,
      uploadPhotos,
    });
    expect(uploadPhotos).not.toHaveBeenCalled();
    expect(result.didPut).toBe(false);
    expect(result.awaitingPhotos).toBe(false);
    expect(MENSAJE_EDIT_DATOS_INCERTOS).toMatch(/confirmar si se guardó/i);
  });

  it("cierre no promete recuperar fotos en memoria", () => {
    expect(MENSAJE_EDIT_FOTOS_CIERRE_SIN_RECUPERAR).toMatch(/no se recuperan/i);
    expect(MENSAJE_EDIT_FOTOS_CIERRE_SIN_RECUPERAR).toMatch(/ya está guardada/i);
  });
});
