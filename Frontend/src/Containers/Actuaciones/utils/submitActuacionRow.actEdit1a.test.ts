import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { submitActuacionRow } from "./submitActuacionRow";
import { actaComprobacionBloqueadaEdicion, actaNotificacionBloqueadaEdicion } from "./actuacionEditRules";

vi.mock("../../../api/gridApi", () => ({
  validateRow: vi.fn(async () => ({ ok: true, errors: {}, normalized: {} })),
}));

vi.mock("../../../api/actuacionesApi", () => ({
  updateActuacion: vi.fn(async (_id: number, body: unknown) => body),
}));

vi.mock("../../../api/actuacionesListApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/actuacionesListApi")>();
  return { ...mod, postQuitarActaCanalActas: vi.fn() };
});

import { updateActuacion } from "../../../api/actuacionesApi";

const mockedUpdateActuacion = vi.mocked(updateActuacion);

const manualRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 501,
    orden_trabajo_numero: "123456",
    fecha_actuacion: "2026-05-10",
    tipo_actuacion: "INSPECCION",
    rubro_nombre: "Bar",
    inspector1: "García",
    inspector2: "López",
    calle: "San Martín",
    numero: "100",
    numero_tipo: "NUMERO",
    doc_nro: "20345678901",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    razon_social: null,
    contraproducencia: "NO_HUBO",
    acta_inspeccion_num: "42",
    can_edit_domicilio: true,
    can_edit_rubro: true,
    ruta_item_id: null,
    observaciones_ejecucion: null,
    ...overrides,
  }) as IActuacionListItem;

async function putBody(
  fullRow: IActuacionListItem,
  originalRow: IActuacionListItem
): Promise<Record<string, unknown>> {
  const result = await submitActuacionRow({
    id: originalRow.id,
    fullRow,
    originalRow,
    skipValidation: true,
    skipUpdate: false,
  });
  expect(result.ok).toBe(true);
  expect(mockedUpdateActuacion).toHaveBeenCalledTimes(1);
  return mockedUpdateActuacion.mock.calls[0][1] as Record<string, unknown>;
}

describe("HOTFIX V1.1-ACT-EDIT.1A actuación manual sin RutaItem", () => {
  beforeEach(() => {
    mockedUpdateActuacion.mockClear();
  });

  it("cambiar solo calle no envía observaciones de RutaItem", async () => {
    const original = manualRow();
    const body = await putBody(manualRow({ calle: "Catamarca" }), original);
    expect(body.calle).toBe("Catamarca");
    expect(body).not.toHaveProperty("observaciones_ejecucion");
    expect(body).not.toHaveProperty("limpiar_contribuyente");
  });

  it("cambiar solo número/referencia no envía observaciones de RutaItem", async () => {
    const original = manualRow();
    const body = await putBody(manualRow({ numero: "250", numero_tipo: "NUMERO" }), original);
    expect(body.numero).toBe("250");
    expect(body).not.toHaveProperty("observaciones_ejecucion");
  });

  it("cambiar solo rubro no envía observaciones de RutaItem", async () => {
    const original = manualRow();
    const body = await putBody(manualRow({ rubro_nombre: "Carnicería" }), original);
    expect(body.rubro_nombre).toBe("Carnicería");
    expect(body).not.toHaveProperty("observaciones_ejecucion");
  });

  it("cambiar nombre de fantasía no exige RutaItem", async () => {
    const original = manualRow();
    const body = await putBody(manualRow({ nombre_local: "Lo de Pérez" }), original);
    expect(body.nombre_local).toBe("Lo de Pérez");
    expect(body).not.toHaveProperty("observaciones_ejecucion");
  });

  it("guardar sin tocar observaciones no invoca lógica de RutaItem", async () => {
    const original = manualRow({ observaciones_ejecucion: null });
    const body = await putBody(original, original);
    expect(body).not.toHaveProperty("observaciones_ejecucion");
    expect(body).not.toHaveProperty("ruta_item_id");
  });

  it("con RutaItem conserva el flujo actual de observaciones", async () => {
    const original = manualRow({
      ruta_item_id: 88,
      observaciones_ejecucion: "Puerta cerrada",
    });
    const body = await putBody(
      manualRow({
        ruta_item_id: 88,
        observaciones_ejecucion: "Volver mañana",
        calle: "San Martín",
      }),
      original
    );
    expect(body.observaciones_ejecucion).toBe("Volver mañana");
  });

  it("guardar sin cambios no desvincula contribuyente", async () => {
    const original = manualRow();
    const body = await putBody(original, original);
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
    expect(body).not.toHaveProperty("contrib_apellido");
    expect(body).not.toHaveProperty("contrib_nombre");
  });

  it("actas con expediente u oficio siguen bloqueadas", () => {
    const row = manualRow({
      notificacion_editable: false,
      comprobacion_editable: false,
      acta_notificacion_num: "200",
      acta_comprobacion_num: "300",
    });
    expect(actaNotificacionBloqueadaEdicion(row)).toBe(true);
    expect(actaComprobacionBloqueadaEdicion(row)).toBe(true);
  });

  it("observaciones modificadas sin RutaItem no viajan en el PUT ni abortan el resto", async () => {
    const original = manualRow({ observaciones_ejecucion: null });
    const body = await putBody(
      manualRow({
        observaciones_ejecucion: "no hay ítem de ruta",
        calle: "Catamarca",
      }),
      original
    );
    expect(body.calle).toBe("Catamarca");
    expect(body).not.toHaveProperty("observaciones_ejecucion");
  });
});
