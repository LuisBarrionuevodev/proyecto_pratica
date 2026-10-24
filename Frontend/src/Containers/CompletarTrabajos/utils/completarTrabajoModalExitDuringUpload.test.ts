import { describe, expect, it } from "vitest";

import {
  shouldBlockCompletarTrabajoModalClose,
  shouldConfirmPauseMediaUploadOnClose,
} from "./completarTrabajoModalExitDuringUpload";

describe("completarTrabajoModalExitDuringUpload (MEDIA.2E.1A)", () => {
  it("no bloquea cierre cuando saving solo por subida activa", () => {
    expect(
      shouldBlockCompletarTrabajoModalClose({
        saving: true,
        mediaSessionActive: true,
        finalizingPorAhora: false,
      })
    ).toBe(false);
  });

  it("bloquea cierre durante guardado de cierre sin sesión de media", () => {
    expect(
      shouldBlockCompletarTrabajoModalClose({
        saving: true,
        mediaSessionActive: false,
        finalizingPorAhora: false,
      })
    ).toBe(true);
  });

  it("bloquea cierre durante finalizar por ahora", () => {
    expect(
      shouldBlockCompletarTrabajoModalClose({
        saving: false,
        mediaSessionActive: true,
        finalizingPorAhora: true,
      })
    ).toBe(true);
  });

  it("confirma pausa solo con sesión de subida activa", () => {
    expect(shouldConfirmPauseMediaUploadOnClose(true)).toBe(true);
    expect(shouldConfirmPauseMediaUploadOnClose(false)).toBe(false);
  });
});
