import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { mergeActuacionAfterOficioCorrection } from "./mergeActuacionAfterOficioCorrection";

function row(partial: Partial<IActuacionListItem>): IActuacionListItem {
  return {
    id: 1,
    orden_trabajo_numero: "1",
    fecha_actuacion: "2026-01-01",
    tipo_actuacion: "VERIFICAR E INFORMAR",
    ...partial,
  } as IActuacionListItem;
}

describe("mergeActuacionAfterOficioCorrection", () => {
  it("POST gana en campos operativos; draft conserva inspectores", () => {
    const correctedRow = row({
      contraproducencia: null,
      resultado_cumplimiento_oficio: "CUMPLE",
      realizo_nueva_inspeccion: false,
      inspector1: "Viejo",
    });
    const pendingDraft = row({
      contraproducencia: "LOCAL CERRADO",
      resultado_cumplimiento_oficio: null,
      realizo_nueva_inspeccion: true,
      inspector1: "Nuevo",
      inspector2: "Segundo",
      acta_inspeccion_num: "999",
    });

    const merged = mergeActuacionAfterOficioCorrection({ correctedRow, pendingDraft });

    expect(merged.contraproducencia).toBeNull();
    expect(merged.resultado_cumplimiento_oficio).toBe("CUMPLE");
    expect(merged.realizo_nueva_inspeccion).toBe(false);
    expect(merged.inspector1).toBe("Nuevo");
    expect(merged.inspector2).toBe("Segundo");
    expect(merged.acta_inspeccion_num).toBe("999");
  });

  it("no reintroduce LOCAL CERRADO del draft stale", () => {
    const merged = mergeActuacionAfterOficioCorrection({
      correctedRow: row({ contraproducencia: null, realizo_nueva_inspeccion: true }),
      pendingDraft: row({ contraproducencia: "LOCAL CERRADO" }),
    });
    expect(merged.contraproducencia).toBeNull();
    expect(merged.realizo_nueva_inspeccion).toBe(true);
  });

  it("POST gana en tipo_actuacion al cambiar subtipo", () => {
    const merged = mergeActuacionAfterOficioCorrection({
      correctedRow: row({
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        resultado_cumplimiento_oficio: "CUMPLE",
        contraproducencia: null,
        realizo_nueva_inspeccion: null,
      }),
      pendingDraft: row({
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: true,
        acta_inspeccion_num: null,
        inspector1: "Inspector Local",
      }),
    });

    expect(merged.tipo_actuacion).toBe("RATIFICACION DE CLAUSURA");
    expect(merged.realizo_nueva_inspeccion).toBeNull();
    expect(merged.inspector1).toBe("Inspector Local");
  });
});
