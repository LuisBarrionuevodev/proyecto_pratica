import { describe, expect, it, vi } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MENSAJE_BLOQUEO_EXPEDIENTE_EDICION,
  MENSAJE_BLOQUEO_INTENTO_POSTERIOR,
  resolveActuacionEditStart,
} from "./actuacionEditRules";

const baseRow = { id: 1 } as IActuacionListItem;

/** Simula la rama de `handleStartEditing` cuando hay bloqueo por expediente. */
function simulateEditStartFeedback(
  row: IActuacionListItem,
  warn: (message: string) => void
): boolean {
  const result = resolveActuacionEditStart(row);
  if (!result.allowed) {
    warn(result.message);
    return false;
  }
  return true;
}

describe("actuacionDetalleEditFeedback", () => {
  it("bloqueo por expediente dispara feedback.warning", () => {
    const warn = vi.fn();
    const allowed = simulateEditStartFeedback({ ...baseRow, comprobacion_editable: false }, warn);
    expect(allowed).toBe(false);
    expect(warn).toHaveBeenCalledWith(MENSAJE_BLOQUEO_EXPEDIENTE_EDICION);
  });

  it("bloqueo por intento posterior dispara feedback.warning", () => {
    const warn = vi.fn();
    const allowed = simulateEditStartFeedback(
      { ...baseRow, actuacion_editable: false, motivo_bloqueo_edicion: MENSAJE_BLOQUEO_INTENTO_POSTERIOR },
      warn
    );
    expect(allowed).toBe(false);
    expect(warn).toHaveBeenCalledWith(MENSAJE_BLOQUEO_INTENTO_POSTERIOR);
  });

  it("sin bloqueo no dispara warning", () => {
    const warn = vi.fn();
    const allowed = simulateEditStartFeedback(baseRow, warn);
    expect(allowed).toBe(true);
    expect(warn).not.toHaveBeenCalled();
  });
});
