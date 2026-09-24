import { describe, expect, it } from "vitest";

import { usaInspeccionNormalReinspeccionOficio } from "./usaInspeccionNormalReinspeccionOficio";

describe("usaInspeccionNormalReinspeccionOficio", () => {
  it("Ratificación Clausura + cualquier resultado → false", () => {
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE CLAUSURA", "")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE CLAUSURA", "SI_INSPECCION")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE CLAUSURA", "NO_INSPECCION")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE CLAUSURA", "CONTRAPRODUCENCIA")).toBe(false);
  });

  it("Ratificación Decomiso + cualquier resultado → false", () => {
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE DECOMISO", "")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE DECOMISO", "SI_INSPECCION")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE DECOMISO", "NO_INSPECCION")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("RATIFICACION DE DECOMISO", "CONTRAPRODUCENCIA")).toBe(false);
  });

  it("Verificar + CONTRAPRODUCENCIA → false", () => {
    expect(usaInspeccionNormalReinspeccionOficio("VERIFICAR E INFORMAR", "CONTRAPRODUCENCIA")).toBe(false);
  });

  it("Verificar + NO_INSPECCION → false", () => {
    expect(usaInspeccionNormalReinspeccionOficio("VERIFICAR E INFORMAR", "NO_INSPECCION")).toBe(false);
  });

  it("Verificar + SI_INSPECCION → true", () => {
    expect(usaInspeccionNormalReinspeccionOficio("VERIFICAR E INFORMAR", "SI_INSPECCION")).toBe(true);
  });

  it("Verificar sin estado → false", () => {
    expect(usaInspeccionNormalReinspeccionOficio("VERIFICAR E INFORMAR", "")).toBe(false);
    expect(usaInspeccionNormalReinspeccionOficio("VERIFICAR E INFORMAR", undefined)).toBe(false);
  });
});
