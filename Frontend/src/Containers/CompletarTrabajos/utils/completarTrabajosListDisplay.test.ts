import { describe, expect, it } from "vitest";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import {
  completarTrabajoDomicilioLinea,
  completarTrabajoEstadoLabel,
  completarTrabajoOrigenTipoSegments,
  completarTrabajoTitularLinea,
} from "./completarTrabajosListDisplay";

function row(partial: Partial<ICompletarTrabajoPendienteRow> = {}): ICompletarTrabajoPendienteRow {
  return {
    id: 1,
    ruta_item_id: 1,
    actuacion_id: null,
    ruta_trabajo_id: 1,
    ruta_grupo_id: 1,
    iniciador_ruta_id: 1,
    grupo_nombre: "G1",
    tipo_iniciador: "RELEVAMIENTO",
    fecha_actuacion: "2026-01-01",
    orden_trabajo_numero: "100",
    iniciador_estado: "PENDIENTE",
    domicilio_texto: "Calle 1",
    estado_operativo: "PENDIENTE",
    observaciones_ejecucion: null,
    calle: "Calle",
    numero: "1",
    rubro_nombre: "Panadería",
    doc_nro: null,
    contrib_apellido: "Gómez",
    contrib_nombre: "Ana",
    razon_social: null,
    nombre_local: null,
    tipo_actuacion: null,
    contraproducencia: null,
    inspectores: [],
    inspector1: null,
    inspector2: null,
    inspector3: null,
    ...partial,
  };
}

describe("completarTrabajosListDisplay", () => {
  it("arma domicilio y origen para cards móviles", () => {
    expect(completarTrabajoDomicilioLinea(row())).toBe("Calle 1");
    const segs = completarTrabajoOrigenTipoSegments(row({ tipo_actuacion: "INSPECCION" }));
    expect(segs.some((s) => s.includes("Origen:"))).toBe(true);
    expect(segs.some((s) => s.includes("Tipo:"))).toBe(true);
  });

  it("prioriza titular local y expone estado operativo", () => {
    expect(completarTrabajoTitularLinea(row({ nombre_local: "La Esquina" }))).toBe("La Esquina");
    expect(completarTrabajoEstadoLabel(row({ estado_operativo: "EN_CURSO" }))).toBe("EN_CURSO");
    expect(completarTrabajoEstadoLabel(row({ estado_operativo: "EN_PROCESO" }))).toBe("EN PROCESO");
  });
});
