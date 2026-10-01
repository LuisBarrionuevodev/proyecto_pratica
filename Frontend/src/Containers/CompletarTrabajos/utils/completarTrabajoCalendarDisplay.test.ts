import { describe, expect, it } from "vitest";

import type { ICompletarTrabajoPendienteDiaResumen } from "../../../api/completarTrabajoApi";
import {
  completarCeldaSurfaceSx,
  formatPendientesDiaDescripcion,
  formatPendientesDiaLabel,
  monthBoundsIso,
  pendientesFooterLabel,
  resolvePendienteCeldaTono,
} from "./completarTrabajoCalendarDisplay";

function row(total: number, fecha = "2026-07-11"): ICompletarTrabajoPendienteDiaResumen {
  return {
    fecha,
    total,
    atrasado: false,
    categoria_calendario: total > 0 ? "CON_PENDIENTES" : "COMPLETO",
  };
}

describe("completarTrabajoCalendarDisplay", () => {
  it("formatPendientesDiaLabel compacto en celda", () => {
    expect(formatPendientesDiaLabel(0)).toBeUndefined();
    expect(formatPendientesDiaLabel(1)).toBe("1!");
    expect(formatPendientesDiaLabel(17)).toBe("17!");
  });

  it("formatPendientesDiaDescripcion para tooltip", () => {
    expect(formatPendientesDiaDescripcion(1)).toBe("1 pendiente");
    expect(formatPendientesDiaDescripcion(17)).toBe("17 pendientes");
  });

  it("pendientesFooterLabel usa total del resumen", () => {
    expect(pendientesFooterLabel(undefined)).toBeUndefined();
    expect(pendientesFooterLabel(row(0))).toBeUndefined();
    expect(pendientesFooterLabel(row(1))).toBe("1!");
    expect(pendientesFooterLabel(row(2))).toBe("2!");
  });

  it("monthBoundsIso devuelve primer y último día del mes", () => {
    const julio = monthBoundsIso(new Date(2026, 6, 1));
    expect(julio).toEqual({ desde: "2026-07-01", hasta: "2026-07-31" });
    const sept = monthBoundsIso(new Date(2026, 8, 15));
    expect(sept).toEqual({ desde: "2026-09-01", hasta: "2026-09-30" });
  });

  describe("resolvePendienteCeldaTono — thresholds exactos", () => {
    it("0 → verde", () => {
      expect(resolvePendienteCeldaTono(row(0))).toBe("verde");
    });

    it("1 → amarillo", () => {
      expect(resolvePendienteCeldaTono(row(1))).toBe("amarillo");
    });

    it("5 → amarillo", () => {
      expect(resolvePendienteCeldaTono(row(5))).toBe("amarillo");
    });

    it("6 → rojo", () => {
      expect(resolvePendienteCeldaTono(row(6))).toBe("rojo");
    });

    it("sin fila → neutral", () => {
      expect(resolvePendienteCeldaTono(undefined)).toBe("neutral");
    });
  });

  describe("fixture histórico julio", () => {
    const julioFixture = new Map<string, ICompletarTrabajoPendienteDiaResumen>([
      ["2026-07-05", row(0, "2026-07-05")],
      ["2026-07-11", row(1, "2026-07-11")],
      ["2026-07-15", row(5, "2026-07-15")],
      ["2026-07-21", row(6, "2026-07-21")],
    ]);

    it("05/07 verde sin footer", () => {
      const r = julioFixture.get("2026-07-05");
      expect(resolvePendienteCeldaTono(r)).toBe("verde");
      expect(pendientesFooterLabel(r)).toBeUndefined();
      expect(completarCeldaSurfaceSx("verde").bgcolor).toContain("--d-calendar-completar-verde-bg");
    });

    it("11/07 amarillo con 1!", () => {
      const r = julioFixture.get("2026-07-11");
      expect(resolvePendienteCeldaTono(r)).toBe("amarillo");
      expect(pendientesFooterLabel(r)).toBe("1!");
    });

    it("15/07 amarillo con 5!", () => {
      const r = julioFixture.get("2026-07-15");
      expect(resolvePendienteCeldaTono(r)).toBe("amarillo");
      expect(pendientesFooterLabel(r)).toBe("5!");
    });

    it("21/07 rojo con 6!", () => {
      const r = julioFixture.get("2026-07-21");
      expect(resolvePendienteCeldaTono(r)).toBe("rojo");
      expect(pendientesFooterLabel(r)).toBe("6!");
      expect(completarCeldaSurfaceSx("rojo").bgcolor).toContain("--d-calendar-completar-rojo-bg");
    });
  });
});
