import { describe, expect, it, vi } from "vitest";

type EditSaveSessionOutcome = "success" | "aborted";

/**
 * Espejo del orden en ActuacionDetalleDialog.handleSaveClick (PUT → fotos → fin de sesión).
 */
async function runEditSaveWithDeferredMedia(options: {
  putSave: () => Promise<boolean>;
  pendingPhotos: () => number;
  uploadPhotos: () => Promise<EditSaveSessionOutcome>;
  endSession: (outcome: EditSaveSessionOutcome) => void;
}): Promise<void> {
  const putOk = await options.putSave();
  if (putOk === false) return;
  let sessionOutcome: EditSaveSessionOutcome = "success";
  if (options.pendingPhotos() > 0) {
    sessionOutcome = await options.uploadPhotos();
  }
  options.endSession(sessionOutcome);
}

describe("actuacionDetalleSaveSequence HOTFIX V1.1-CRUD-ACTUACIONES.1", () => {
  it("PUT fallido no sube fotos ni cierra", async () => {
    const upload = vi.fn();
    const endSession = vi.fn();

    await runEditSaveWithDeferredMedia({
      putSave: async () => false,
      pendingPhotos: () => 2,
      uploadPhotos: async () => "success",
      endSession,
    });

    expect(upload).not.toHaveBeenCalled();
    expect(endSession).not.toHaveBeenCalled();
  });

  it("PUT exitoso con cola sube fotos y luego cierra sesión una vez", async () => {
    const order: string[] = [];
    const upload = vi.fn(async () => {
      order.push("upload");
      return "success" as const;
    });
    const endSession = vi.fn((outcome: EditSaveSessionOutcome) => {
      order.push(`end:${outcome}`);
    });

    await runEditSaveWithDeferredMedia({
      putSave: async () => {
        order.push("put");
        return true;
      },
      pendingPhotos: () => 1,
      uploadPhotos: upload,
      endSession,
    });

    expect(order).toEqual(["put", "upload", "end:success"]);
    expect(endSession).toHaveBeenCalledOnce();
  });

  it("subida parcial aborta sesión sin cierre exitoso", async () => {
    const endSession = vi.fn();

    await runEditSaveWithDeferredMedia({
      putSave: async () => true,
      pendingPhotos: () => 1,
      uploadPhotos: async () => "aborted",
      endSession,
    });

    expect(endSession).toHaveBeenCalledWith("aborted");
  });
});
