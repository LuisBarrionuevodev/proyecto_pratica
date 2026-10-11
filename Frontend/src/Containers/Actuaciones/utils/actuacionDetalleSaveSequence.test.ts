import { describe, expect, it, vi } from "vitest";

/**
 * Espejo del orden en ActuacionDetalleDialog.handleSaveClick (PUT → fotos → cierre).
 */
async function runEditSaveWithDeferredMedia(options: {
  putSave: () => Promise<boolean>;
  pendingPhotos: () => number;
  uploadPhotos: () => Promise<void>;
  close: () => void;
}): Promise<void> {
  const putOk = await options.putSave();
  if (putOk === false) return;
  if (options.pendingPhotos() > 0) {
    await options.uploadPhotos();
  }
  options.close();
}

describe("actuacionDetalleSaveSequence HOTFIX V1.1-CRUD-ACTUACIONES.1", () => {
  it("PUT fallido no sube fotos ni cierra", async () => {
    const upload = vi.fn();
    const close = vi.fn();

    await runEditSaveWithDeferredMedia({
      putSave: async () => false,
      pendingPhotos: () => 2,
      uploadPhotos: upload,
      close,
    });

    expect(upload).not.toHaveBeenCalled();
    expect(close).not.toHaveBeenCalled();
  });

  it("PUT exitoso con cola sube fotos y luego cierra", async () => {
    const order: string[] = [];
    const upload = vi.fn(async () => {
      order.push("upload");
    });
    const close = vi.fn(() => {
      order.push("close");
    });

    await runEditSaveWithDeferredMedia({
      putSave: async () => {
        order.push("put");
        return true;
      },
      pendingPhotos: () => 1,
      uploadPhotos: upload,
      close,
    });

    expect(order).toEqual(["put", "upload", "close"]);
  });
});
