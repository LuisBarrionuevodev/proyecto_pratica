import { describe, expect, it } from "vitest";
import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import {
  lineasEvidenciasPendientes,
  rowTieneEvidenciasPendientes,
} from "./completarTrabajoMediaPendingDisplay";

const baseRow = { ruta_item_id: 1 } as ICompletarTrabajoPendienteRow;

describe("completarTrabajoMediaPendingDisplay", () => {
  it("detecta trabajo guardado con evidencias pendientes", () => {
    const row = {
      ...baseRow,
      trabajo_guardado_evidencias_pendientes: true,
      media_resumen: {
        foto_acta: { ready: 1, pending: 2, max: 7, pendientes: 6 },
        tiene_evidencias_pendientes: true,
      },
    } as ICompletarTrabajoPendienteRow;
    expect(rowTieneEvidenciasPendientes(row)).toBe(true);
    const lines = lineasEvidenciasPendientes(row.media_resumen ?? null);
    expect(lines[0]).toContain("Actas: 2 pendientes de 7");
  });
});
