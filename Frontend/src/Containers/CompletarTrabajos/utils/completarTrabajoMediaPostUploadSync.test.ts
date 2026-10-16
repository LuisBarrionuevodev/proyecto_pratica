import { describe, expect, it, vi } from "vitest";
import { waitForCompletarTrabajoEvidenciasBackendSync } from "./completarTrabajoMediaPostUploadSync";

const detalleCompleto = {
  ui_policy: { solo_evidencias_pendientes: false, cierre_alfanumerico_readonly: true },
  row: {
    estado_operativo: "FINALIZADO",
    trabajo_guardado_evidencias_pendientes: false,
    media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
  },
  inspectores_grupo: [],
  tipo_actuacion_esperado: null,
};

const detallePendiente = {
  ui_policy: { solo_evidencias_pendientes: true },
  row: {
    media_resumen: { tiene_evidencias_pendientes: true, evidencias_pendientes_total: 1 },
  },
  inspectores_grupo: [],
  tipo_actuacion_esperado: null,
};

describe("waitForCompletarTrabajoEvidenciasBackendSync", () => {
  it("cierra en el segundo intento si el primero aún reporta pendientes", async () => {
    const fetchDetalle = vi
      .fn()
      .mockResolvedValueOnce(detallePendiente)
      .mockResolvedValueOnce(detalleCompleto);
    const sleep = vi.fn().mockResolvedValue(undefined);

    const result = await waitForCompletarTrabajoEvidenciasBackendSync(9, {
      fetchDetalle,
      fetchArchivos: vi.fn().mockResolvedValue({
        foto_acta: [],
        foto_documentacion_local: [],
        foto_inspeccion: [],
      }),
      maxAttempts: 3,
      delayMs: 10,
      sleep,
    });

    expect(result).toEqual({ status: "completo" });
    expect(fetchDetalle).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledTimes(1);
  });

  it("tras agotar intentos devuelve pendiente", async () => {
    const fetchDetalle = vi.fn().mockResolvedValue(detallePendiente);
    const result = await waitForCompletarTrabajoEvidenciasBackendSync(3, {
      fetchDetalle,
      fetchArchivos: vi.fn(),
      maxAttempts: 2,
      delayMs: 0,
      sleep: vi.fn().mockResolvedValue(undefined),
    });
    expect(result).toEqual({ status: "pendiente" });
    expect(fetchDetalle).toHaveBeenCalledTimes(2);
  });
});
