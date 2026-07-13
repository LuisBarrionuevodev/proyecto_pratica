import { describe, expect, it } from "vitest";

import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildOrdenTrabajoDepartamentalDocumentModel, listRutaItemsSinOtAsignada } from "./buildOrdenTrabajoDepartamentalDocumentModel";

const rutaBase: IRutaTrabajo = {
  id: 1,
  fecha: "2026-07-11",
  turno: "MANIANA",
  estado_ruta: "PUBLICADA",
  numero: 3,
  observaciones: null,
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

const grupoBase: IRutaGrupoMin = {
  id: 10,
  ruta_trabajo_id: 1,
  nombre: "Grupo 1",
  estado: "ACTIVO",
  inspectores: [
    { id: 1, inspector_id: 100, inspector_nombre: "Pérez, Juan", inspector_legajo: "1234" },
    { id: 2, inspector_id: 101, inspector_nombre: "García, Ana", inspector_legajo: "5678" },
  ],
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

function itemConOt(id: number, overrides: Partial<IRutaItemMin> = {}): IRutaItemMin {
  return {
    id,
    ruta_trabajo_id: 1,
    ruta_grupo_id: 10,
    iniciador_ruta_id: 200 + id,
    tipo_iniciador: "RELEVAMIENTO",
    orden_trabajo_id: 50 + id,
    actuacion_id: null,
    orden_trabajo: { id: 50 + id, numero_acta: String(id).padStart(6, "0"), anio: 2026, mes: 7 },
    estado_ruta_item: "ASIGNADO",
    deleted_at: null,
    domicilio_texto: "San Martín 1000",
    rubro_nombre: "Carnicería",
    nombre_fantasia: "El Toro",
    ...overrides,
  };
}

describe("buildOrdenTrabajoDepartamentalDocumentModel", () => {
  it("genera una orden por ítem con OT", () => {
    const model = buildOrdenTrabajoDepartamentalDocumentModel(
      rutaBase,
      [grupoBase],
      [itemConOt(1), itemConOt(2, { domicilio_texto: "Chacabuco Y Piedras" })]
    );
    expect(model.ordenes).toHaveLength(2);
    expect(model.ordenes[0]?.numeroOt).toBe("000001");
    expect(model.ordenes[0]?.inspectoresTexto).toContain("Pérez");
    expect(model.ordenes[0]?.domicilioLinea).toBe("San Martín 980-1000");
    expect(model.ordenes[1]?.domicilioLinea).toBe("Chacabuco y Piedras");
    expect(model.turnoLegible).toBe("Mañana");
  });

  it("omite ítems sin OT", () => {
    const sinOt = itemConOt(3, { orden_trabajo: null, orden_trabajo_id: null });
    const model = buildOrdenTrabajoDepartamentalDocumentModel(rutaBase, [grupoBase], [sinOt]);
    expect(model.ordenes).toHaveLength(0);
  });

  it("listRutaItemsSinOtAsignada detecta ítems sin OT", () => {
    const conOt = itemConOt(1);
    const sinOt = itemConOt(2, { orden_trabajo: null, orden_trabajo_id: null, domicilio_texto: "Laprida 500" });
    const omitidos = listRutaItemsSinOtAsignada([conOt, sinOt]);
    expect(omitidos).toHaveLength(1);
    expect(omitidos[0]?.itemId).toBe(2);
    expect(omitidos[0]?.domicilioTexto).toBe("Laprida 500");
  });

  it("no incluye rubro ni fantasía en domicilio", () => {
    const model = buildOrdenTrabajoDepartamentalDocumentModel(rutaBase, [grupoBase], [itemConOt(1)]);
    const linea = model.ordenes[0]?.domicilioLinea ?? "";
    expect(linea).not.toContain("Carnicería");
    expect(linea).not.toContain("Toro");
  });
});
