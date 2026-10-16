import { describe, expect, it } from "vitest";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../../../features/media/mediaConstants";
import {
  detalleConfirmaCompletarTrabajoSinEvidenciasPendientes,
  fetchDetalleConfirmaSinEvidenciasPendientesDetailed,
  isLocalCompletarTrabajoMediaQueueFinished,
} from "./completarTrabajoEvidenciasConfirm";

function item(phase: MediaQueuedFile["phase"], archivoId: number | null): MediaQueuedFile {
  return {
    localId: "x",
    file: new File(["a"], "a.jpg", { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase,
    progressPct: 0,
    errorMessage: null,
    archivoId,
    previewUrl: null,
  };
}

describe("completarTrabajoEvidenciasConfirm", () => {
  it("detalle completo sin evidencias pendientes", () => {
    expect(
      detalleConfirmaCompletarTrabajoSinEvidenciasPendientes({
        ui_policy: { solo_evidencias_pendientes: true, cierre_alfanumerico_readonly: true },
        row: {
          trabajo_guardado_evidencias_pendientes: false,
          media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
        },
      } as never)
    ).toBe(true);
  });

  it("fetch detalle con error HTTP no se interpreta como completo", async () => {
    const result = await fetchDetalleConfirmaSinEvidenciasPendientesDetailed(1, async () => {
      throw new Error("400");
    });
    expect(result).toEqual({ status: "error" });
  });

  it("FINALIZADO sincronizado sin pendientes → completo", async () => {
    const result = await fetchDetalleConfirmaSinEvidenciasPendientesDetailed(2, async () => ({
      ui_policy: {
        solo_evidencias_pendientes: false,
        cierre_alfanumerico_readonly: true,
      },
      row: {
        estado_operativo: "FINALIZADO",
        iniciador_estado: "FINALIZADO",
        trabajo_guardado_evidencias_pendientes: false,
        media_resumen: { tiene_evidencias_pendientes: false, evidencias_pendientes_total: 0 },
      },
      inspectores_grupo: [],
      tipo_actuacion_esperado: null,
    }));
    expect(result).toEqual({ status: "completo" });
  });

  it("cola all READY sin uploadable cuenta como finalizada", () => {
    expect(isLocalCompletarTrabajoMediaQueueFinished([item("ready", 1), item("ready", 2)])).toBe(
      true
    );
    expect(isLocalCompletarTrabajoMediaQueueFinished([item("error", null)])).toBe(false);
    expect(isLocalCompletarTrabajoMediaQueueFinished([item("error", 9)])).toBe(true);
  });
});
