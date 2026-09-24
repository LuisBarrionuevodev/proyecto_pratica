import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../api/actuacionesListApi";
import {
  resolveCumplimientoUiFromPersisted,
  resolveReinspeccionOficioFormContext,
  realizoNuevaInspeccionFromPersisted,
} from "./resolveReinspeccionOficioFormContext";

function baseRow(overrides: Partial<IActuacionListItem> = {}): IActuacionListItem {
  return {
    id: 1,
    orden_trabajo_numero: "1",
    fecha_actuacion: "2026-01-01",
    tipo_actuacion: "Inspección",
    contraproducencia: null,
    ...overrides,
  } as IActuacionListItem;
}

describe("resolveCumplimientoUiFromPersisted", () => {
  it("reconstruye CUMPLE", () => {
    expect(resolveCumplimientoUiFromPersisted({ resultado_cumplimiento_oficio: "CUMPLE" })).toBe("CUMPLE");
  });

  it("reconstruye contraproducencia sin resultado", () => {
    expect(
      resolveCumplimientoUiFromPersisted({
        resultado_cumplimiento_oficio: null,
        contraproducencia: "NO SE RATIFICÓ",
      })
    ).toBe("CONTRAPRODUCENCIA");
  });

  it("reconstruye NO_CUMPLE", () => {
    expect(resolveCumplimientoUiFromPersisted({ resultado_cumplimiento_oficio: "NO_CUMPLE" })).toBe("NO_CUMPLE");
  });
});

describe("realizoNuevaInspeccionFromPersisted", () => {
  it("mapea true/false/null", () => {
    expect(realizoNuevaInspeccionFromPersisted(true)).toBe("si");
    expect(realizoNuevaInspeccionFromPersisted(false)).toBe("no");
    expect(realizoNuevaInspeccionFromPersisted(null)).toBe("");
  });
});

describe("resolveReinspeccionOficioFormContext", () => {
  it("Clausura CUMPLE", () => {
    const ctx = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        resultado_cumplimiento_oficio: "CUMPLE",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(ctx?.esRatificacion).toBe(true);
    expect(ctx?.cumplimientoUi).toBe("CUMPLE");
    expect(ctx?.subtipoReadonly).toBe(false);
  });

  it("Clausura contra histórica", () => {
    const ctx = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        contraproducencia: "NO SE RATIFICÓ",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(ctx?.cumplimientoUi).toBe("CONTRAPRODUCENCIA");
    expect(ctx?.contraproducencia).toBe("NO SE RATIFICÓ");
  });

  it("Decomiso CUMPLE y contra", () => {
    const cumple = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "RATIFICACION DE DECOMISO",
        resultado_cumplimiento_oficio: "CUMPLE",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(cumple?.esRatificacion).toBe(true);

    const contra = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "RATIFICACION DE DECOMISO",
        contraproducencia: "NO PAGÓ TODAVÍA EL DECOMISO",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(contra?.cumplimientoUi).toBe("CONTRAPRODUCENCIA");
  });

  it("Verificar true/false/null", () => {
    const si = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: true,
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(si?.esVerificar).toBe(true);
    expect(si?.realizoNuevaInspeccion).toBe("si");

    const no = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: false,
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(no?.realizoNuevaInspeccion).toBe("no");

    const amb = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: null,
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(amb?.realizoNuevaInspeccion).toBe("");
    expect(amb?.verificarEstadoOperativo).toBe("");
  });

  it("Verificar contra pura", () => {
    const ctx = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "VERIFICAR E INFORMAR",
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: null,
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(ctx?.verificarEstadoOperativo).toBe("CONTRAPRODUCENCIA");
  });

  it("Verificar híbrido", () => {
    const ctx = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "VERIFICAR E INFORMAR",
        contraproducencia: "LOCAL CERRADO",
        realizo_nueva_inspeccion: true,
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      }),
      mode: "edit",
    });
    expect(ctx?.verificarEstadoOperativo).toBe("INCONSISTENTE");
  });

  it("circuito no oficio retorna null en edit", () => {
    const ctx = resolveReinspeccionOficioFormContext({
      row: baseRow({
        tipo_actuacion: "Inspección",
        documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
      }),
      mode: "edit",
    });
    expect(ctx).toBeNull();
  });
});
