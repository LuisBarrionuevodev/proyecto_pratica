import { describe, expect, it, vi } from "vitest";

import type { ICompletarTrabajoDetalleResponse } from "../../../api/completarTrabajoApi";

vi.mock("../../../api/completarTrabajoApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/completarTrabajoApi")>();
  return {
    ...mod,
    getCompletarTrabajoDetalle: vi.fn(),
  };
});
import {
  classifyCompletarTrabajoDetalle,
  tryRecoverCompletarTrabajoTrasErrorRed,
} from "./completarTrabajoPostErrorRecovery";

function detalle(partial: Partial<ICompletarTrabajoDetalleResponse>): ICompletarTrabajoDetalleResponse {
  return {
    row: {
      id: 1,
      ruta_item_id: 1,
      actuacion_id: 1,
      ruta_trabajo_id: 1,
      ruta_grupo_id: 1,
      iniciador_ruta_id: 1,
      grupo_nombre: "G",
      tipo_iniciador: "RELEVAMIENTO",
      fecha_actuacion: "2026-01-01",
      orden_trabajo_numero: "000001",
      iniciador_estado: "EN_PROCESO",
      domicilio_texto: "X 1",
      estado_operativo: "PENDIENTE",
      observaciones_ejecucion: null,
      calle: "X",
      numero: "1",
      rubro_nombre: "R",
      doc_nro: "1",
      contrib_apellido: "A",
      contrib_nombre: "B",
      razon_social: null,
      nombre_local: null,
      tipo_actuacion: null,
      contraproducencia: null,
      inspectores: [],
      inspector1: null,
      inspector2: null,
      inspector3: null,
      ...partial.row,
    },
    ui_policy: {
      recurso_logico: "actuacion",
      ancla_operativa: "ruta_item_id",
      orden_trabajo_y_fecha_readonly: true,
      inspectores_readonly: true,
      previas_visible: false,
      post_cierre: "",
      ...partial.ui_policy,
    },
    ...partial,
  };
}

describe("classifyCompletarTrabajoDetalle", () => {
  it("marca completo cuando cierre guardado y sin pendientes", () => {
    const status = classifyCompletarTrabajoDetalle(
      detalle({
        ui_policy: { solo_evidencias_pendientes: true, cierre_alfanumerico_readonly: true },
        row: {
          trabajo_guardado_evidencias_pendientes: false,
          media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
        },
      })
    );
    expect(status).toBe("completo");
  });

  it("marca guardado_fotos_pendientes cuando faltan evidencias", () => {
    const status = classifyCompletarTrabajoDetalle(
      detalle({
        ui_policy: { solo_evidencias_pendientes: true },
        row: {
          media_resumen: { tiene_evidencias_pendientes: true, evidencias_pendientes_total: 2 },
        },
      })
    );
    expect(status).toBe("guardado_fotos_pendientes");
  });

  it("marca no_guardado si no hay señales de cierre", () => {
    expect(classifyCompletarTrabajoDetalle(detalle({}))).toBe("no_guardado");
  });
});

describe("tryRecoverCompletarTrabajoTrasErrorRed", () => {
  it("no invoca onNoGuardado cuando el trabajo quedó completo", async () => {
    const { getCompletarTrabajoDetalle } = await import("../../../api/completarTrabajoApi");
    vi.mocked(getCompletarTrabajoDetalle).mockResolvedValueOnce(
      detalle({
        ui_policy: { solo_evidencias_pendientes: true },
        row: {
          media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
        },
      })
    );
    const onCompleto = vi.fn();
    const onGuardado = vi.fn();
    const onNoGuardado = vi.fn();
    const ok = await tryRecoverCompletarTrabajoTrasErrorRed(9, {
      onCompleto,
      onGuardadoFotosPendientes: onGuardado,
      onNoGuardado,
    });
    expect(ok).toBe(true);
    expect(onCompleto).toHaveBeenCalledTimes(1);
    expect(onNoGuardado).not.toHaveBeenCalled();
  });
});
