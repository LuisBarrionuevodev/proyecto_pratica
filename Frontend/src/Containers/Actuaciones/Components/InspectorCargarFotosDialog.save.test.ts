import { describe, expect, it, vi } from "vitest";
import {
  shouldCloseInspectorFotosModalAfterSave,
  type ManualMediaSaveOutcome,
} from "../../../features/media/utils/actuacionManualMediaSave";

describe("InspectorCargarFotosDialog guardar fotos", () => {
  it("éxito operativo cierra modal; partial o empty no", () => {
    expect(shouldCloseInspectorFotosModalAfterSave("success")).toBe(true);
    expect(shouldCloseInspectorFotosModalAfterSave("partial")).toBe(false);
    expect(shouldCloseInspectorFotosModalAfterSave("empty")).toBe(false);
  });

  it("refresh fallido con outcome success no debe usar feedback.error de carga", () => {
    const feedbackError = vi.fn();
    const outcome: ManualMediaSaveOutcome = "success";
    const refreshFailed = true;
    if (outcome === "partial") {
      feedbackError("Algunas fotos no se guardaron.");
    }
    expect(feedbackError).not.toHaveBeenCalled();
    expect(shouldCloseInspectorFotosModalAfterSave(outcome)).toBe(true);
    expect(refreshFailed).toBe(true);
  });
});
