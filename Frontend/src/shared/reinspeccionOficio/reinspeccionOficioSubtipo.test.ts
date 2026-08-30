import { describe, expect, it } from "vitest";

import { tipoIniciadorDesdeSubtipoActuacionOficio } from "./reinspeccionOficioSubtipo";

describe("tipoIniciadorDesdeSubtipoActuacionOficio", () => {
  it("mapea los tres subtipos canónicos", () => {
    expect(tipoIniciadorDesdeSubtipoActuacionOficio("RATIFICACION DE CLAUSURA")).toBe(
      "RATIFICACION_CLAUSURA_OFICIO"
    );
    expect(tipoIniciadorDesdeSubtipoActuacionOficio("RATIFICACION DE DECOMISO")).toBe(
      "RATIFICACION_DECOMISO_OFICIO"
    );
    expect(tipoIniciadorDesdeSubtipoActuacionOficio("VERIFICAR E INFORMAR")).toBe(
      "VERIFICAR_INFORMAR_OFICIO"
    );
  });
});
