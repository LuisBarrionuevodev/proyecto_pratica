import { describe, expect, it } from "vitest";

import type { ICompletarTrabajoPendienteDiaResumen } from "../../../api/completarTrabajoApi";
import {
  formatPendientesDiaLabel,
  pendientesFooterLabel,
} from "./completarTrabajoCalendarDisplay";

function row(total: number): ICompletarTrabajoPendienteDiaResumen {
  return {
    fecha: "2026-05-10",
    total,
    atrasado: false,
    categoria_calendario: total > 0 ? "CON_PENDIENTES" : "COMPLETO",
  };
}

describe("completarTrabajoCalendarDisplay", () => {
  it("formatPendientesDiaLabel singular y plural", () => {
    expect(formatPendientesDiaLabel(0)).toBeUndefined();
    expect(formatPendientesDiaLabel(1)).toBe("1 pendiente");
    expect(formatPendientesDiaLabel(2)).toBe("2 pendientes");
  });

  it("pendientesFooterLabel usa total del resumen", () => {
    expect(pendientesFooterLabel(undefined)).toBeUndefined();
    expect(pendientesFooterLabel(row(0))).toBeUndefined();
    expect(pendientesFooterLabel(row(1))).toBe("1 pendiente");
    expect(pendientesFooterLabel(row(2))).toBe("2 pendientes");
  });
});
