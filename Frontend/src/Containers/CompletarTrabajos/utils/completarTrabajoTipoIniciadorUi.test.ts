import { describe, expect, it } from "vitest";

import {
  esFlujoCierreOficio,
  esFlujoCumplimientoRatificacion,
  esFlujoVerificarInformar,
  esRatificacionOficio,
  esReinspeccionOficioGenerico,
  esReinspeccionOficioPendienteSubtipo,
  esSubtipoActuacionOficioValido,
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

  it("esReinspeccionOficioPendienteSubtipo detecta genérico sin subtipo válido", () => {
    expect(esReinspeccionOficioPendienteSubtipo("REINSPECCION_OFICIO", null)).toBe(true);
    expect(esReinspeccionOficioPendienteSubtipo("REINSPECCION_OFICIO", "")).toBe(true);
    expect(esReinspeccionOficioPendienteSubtipo("REINSPECCION_OFICIO", "REINSPECCION")).toBe(true);
    expect(esReinspeccionOficioPendienteSubtipo("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA")).toBe(
      false
    );
    expect(esReinspeccionOficioPendienteSubtipo("REINSPECCION_NOTIFICACION", null)).toBe(false);
  });

  it("esSubtipoActuacionOficioValido acepta solo los tres subtipos oficio", () => {
    expect(esSubtipoActuacionOficioValido("RATIFICACION DE CLAUSURA")).toBe(true);
    expect(esSubtipoActuacionOficioValido("RATIFICACION DE DECOMISO")).toBe(true);
    expect(esSubtipoActuacionOficioValido("VERIFICAR E INFORMAR")).toBe(true);
    expect(esSubtipoActuacionOficioValido("REINSPECCION")).toBe(false);
  });

  it("gate inspección normal: pendiente subtipo oculta flujo normal", () => {
    const pendiente = esReinspeccionOficioPendienteSubtipo("REINSPECCION_OFICIO", null);
    const cumplimiento = esFlujoCumplimientoRatificacion("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA");
    const verificar = esFlujoVerificarInformar("REINSPECCION_OFICIO", "VERIFICAR E INFORMAR");
    const verificarSi = verificar && "si" === "si";
    const muestraNormalPendiente = !pendiente && !cumplimiento && (!verificar || verificarSi);
    const muestraNormalRatificacion =
      !esReinspeccionOficioPendienteSubtipo("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA") &&
      !esFlujoCumplimientoRatificacion("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA") &&
      (!esFlujoVerificarInformar("REINSPECCION_OFICIO", "RATIFICACION DE CLAUSURA") || false);
    expect(muestraNormalPendiente).toBe(false);
    expect(muestraNormalRatificacion).toBe(false);
  });
});
