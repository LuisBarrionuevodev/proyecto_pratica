import { describe, expect, it } from "vitest";

import {
  CONTRAPRODUCCION_NO_PAGO_DECOMISO,
  CONTRAPRODUCCION_NO_SE_RATIFICO,
  labelTipoActuacionReinspeccionOficio,
  tipoActuacionReinspeccionOficioOpts,
  filtrarContraproducenciaOficioPorTipoActuacion,
} from "./completarTrabajoReinspeccionOficioUi";

describe("completarTrabajoReinspeccionOficioUi", () => {
  it("expone labels humanos para tipos de actuación por oficio", () => {
    expect(labelTipoActuacionReinspeccionOficio("RATIFICACION DE CLAUSURA")).toBe(
      "Ratificación de clausura"
    );
    expect(labelTipoActuacionReinspeccionOficio("RATIFICACION DE DECOMISO")).toBe(
      "Ratificación de decomiso"
    );
    expect(labelTipoActuacionReinspeccionOficio("VERIFICAR E INFORMAR")).toBe("Verificar e informar");
    const opts = tipoActuacionReinspeccionOficioOpts();
    expect(opts.some((o) => o.label.includes("RATIFICACION"))).toBe(false);
    expect(opts.some((o) => o.label === "Ratificación de clausura")).toBe(true);
  });

  it("filtra contras de oficio por subtipo", () => {
    const base = ["LOCAL CERRADO", CONTRAPRODUCCION_NO_SE_RATIFICO, CONTRAPRODUCCION_NO_PAGO_DECOMISO];
    const clausura = filtrarContraproducenciaOficioPorTipoActuacion(base, "RATIFICACION DE CLAUSURA");
    expect(clausura).toContain(CONTRAPRODUCCION_NO_SE_RATIFICO);
    expect(clausura).not.toContain(CONTRAPRODUCCION_NO_PAGO_DECOMISO);

    const decomiso = filtrarContraproducenciaOficioPorTipoActuacion(base, "RATIFICACION DE DECOMISO");
    expect(decomiso).toContain(CONTRAPRODUCCION_NO_PAGO_DECOMISO);
    expect(decomiso).not.toContain(CONTRAPRODUCCION_NO_SE_RATIFICO);
  });
});
