import { describe, expect, it } from "vitest";

import {
  esFlujoCierreOficio,
  esFlujoCumplimientoRatificacion,
  esFlujoVerificarInformar,
  esRatificacionOficio,
  esReinspeccionOficioGenerico,
  esVerificarInformarOficio,
  tipoActuacionEfectivoOficio,
  tipoActuacionFijoDesdeIniciadorOficio,
} from "./completarTrabajoTipoIniciadorUi";

describe("completarTrabajoTipoIniciadorUi", () => {
  it("ratificaciones promovidas usan flujo de cierre oficio", () => {
    expect(esFlujoCierreOficio("RATIFICACION_CLAUSURA_OFICIO")).toBe(true);
    expect(esFlujoCierreOficio("RATIFICACION_DECOMISO_OFICIO")).toBe(true);
    expect(esReinspeccionOficioGenerico("RATIFICACION_CLAUSURA_OFICIO")).toBe(false);
  });

  it("verificar e informar no usa flujo simple de ratificación", () => {
    expect(esVerificarInformarOficio("VERIFICAR_INFORMAR_OFICIO")).toBe(true);
    expect(esFlujoCierreOficio("VERIFICAR_INFORMAR_OFICIO")).toBe(false);
    expect(esRatificacionOficio("VERIFICAR_INFORMAR_OFICIO")).toBe(false);
  });

  it("tipo fijo desde iniciador promovido", () => {
    expect(tipoActuacionFijoDesdeIniciadorOficio("RATIFICACION_CLAUSURA_OFICIO")).toBe(
      "RATIFICACION DE CLAUSURA"
    );
    expect(tipoActuacionEfectivoOficio("RATIFICACION_DECOMISO_OFICIO", null)).toBe(
      "RATIFICACION DE DECOMISO"
    );
  });

  it("verificar e informar distingue flujo de cumplimiento ratificación", () => {
    expect(esFlujoVerificarInformar("VERIFICAR_INFORMAR_OFICIO")).toBe(true);
    expect(esFlujoVerificarInformar("REINSPECCION_OFICIO", "VERIFICAR E INFORMAR")).toBe(true);
    expect(esFlujoCumplimientoRatificacion("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA")).toBe(
      true
    );
    expect(esFlujoCumplimientoRatificacion("REINSPECCION_OFICIO", "VERIFICAR E INFORMAR")).toBe(
      false
    );
    expect(esFlujoCumplimientoRatificacion("RATIFICACION_CLAUSURA_OFICIO")).toBe(true);
  });
});
