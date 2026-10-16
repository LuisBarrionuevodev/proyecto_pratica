import { describe, expect, it } from "vitest";
import {
  isCompletarTrabajoOperativoFinalizado,
  isCompletarTrabajoSoloFotosMode,
} from "./completarTrabajoSoloFotosMode";

describe("isCompletarTrabajoSoloFotosMode", () => {
  it("activa con ui_policy.solo_evidencias_pendientes", () => {
    expect(
      isCompletarTrabajoSoloFotosMode({ solo_evidencias_pendientes: true }, null)
    ).toBe(true);
  });

  it("activa con cierre_alfanumerico_readonly", () => {
    expect(
      isCompletarTrabajoSoloFotosMode({ cierre_alfanumerico_readonly: true }, null)
    ).toBe(true);
  });

  it("activa con trabajo_guardado_evidencias_pendientes en fila", () => {
    expect(
      isCompletarTrabajoSoloFotosMode(null, {
        trabajo_guardado_evidencias_pendientes: true,
        estado_operativo: "FINALIZADO",
        iniciador_estado: "FINALIZADO",
      })
    ).toBe(true);
  });

  it("activa con FINALIZADO y evidencias pendientes en resumen", () => {
    expect(
      isCompletarTrabajoSoloFotosMode(null, {
        estado_operativo: "FINALIZADO",
        iniciador_estado: "FINALIZADO",
        media_resumen: { evidencias_pendientes_total: 2, tiene_evidencias_pendientes: true },
      })
    ).toBe(true);
  });

  it("no activa en EN_PROCESO sin señales de cierre previo", () => {
    expect(
      isCompletarTrabajoSoloFotosMode(null, {
        estado_operativo: "EN_PROCESO",
        iniciador_estado: "EN_PROCESO",
        media_resumen: { evidencias_pendientes_total: 0, tiene_evidencias_pendientes: false },
      })
    ).toBe(false);
  });

  it("no activa en FINALIZADO sin pendientes reales", () => {
    expect(
      isCompletarTrabajoSoloFotosMode(null, {
        estado_operativo: "FINALIZADO",
        iniciador_estado: "FINALIZADO",
        media_resumen: { evidencias_pendientes_total: 0, tiene_evidencias_pendientes: false },
      })
    ).toBe(false);
  });
});

describe("isCompletarTrabajoOperativoFinalizado", () => {
  it("detecta FINALIZADO en estado_operativo", () => {
    expect(
      isCompletarTrabajoOperativoFinalizado({
        estado_operativo: "FINALIZADO",
        iniciador_estado: "EN_PROCESO",
      })
    ).toBe(true);
  });
});
