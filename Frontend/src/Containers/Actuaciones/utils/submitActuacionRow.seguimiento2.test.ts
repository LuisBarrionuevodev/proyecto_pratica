import { describe, expect, it, vi, beforeEach } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { submitActuacionRow } from "./submitActuacionRow";

vi.mock("../../../api/actuacionesApi", () => ({
  updateActuacion: vi.fn(async (_id: number, body: unknown) => body),
}));

vi.mock("../../../api/gridApi", () => ({
  validateRow: vi.fn(async () => ({ ok: true })),
}));

import { updateActuacion } from "../../../api/actuacionesApi";

const carnetPolicy = {
  mostrar_solicitud_carnet_manipulador: true,
  mostrar_subsanacion_notificacion: false,
  puede_editar_seguimiento: true,
};

const subsPolicy = {
  mostrar_solicitud_carnet_manipulador: false,
  mostrar_subsanacion_notificacion: true,
  puede_editar_seguimiento: true,
};

const baseRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 42,
    orden_trabajo_numero: "12345",
    fecha_actuacion: "2026-06-01",
    rubro_nombre: "Panadería",
    inspector1: "Inspector A",
    inspector2: "Inspector B",
    inspector3: null,
    calle: "Mitre",
    numero: "100",
    tipo_actuacion: "Inspección",
    contraproducencia: "No",
    doc_nro: "20123456789",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    acta_inspeccion_num: "100",
    acta_notificacion_num: null,
    notificacion_motivo_1: null,
    notificacion_motivo_2: null,
    notificacion_motivo_3: null,
    acta_comprobacion_num: null,
    comprobacion_motivo: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    decomiso_kilos_total: null,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
    ruta_item_id: 9,
    ui_policy: carnetPolicy,
    solicita_carnet_manipulador: false,
    telefono_contacto_solicitud_carnet: null,
    faltas_notificacion_subsanadas: null,
    observaciones_ejecucion: "original",
    ...overrides,
  }) as IActuacionListItem;

async function putBody(
  fullRow: IActuacionListItem,
  originalRow: IActuacionListItem
): Promise<Record<string, unknown>> {
  const result = await submitActuacionRow({
    id: 42,
    fullRow,
    originalRow,
    skipValidation: true,
    skipUpdate: false,
  });
  expect(result.ok).toBe(true);
  expect(updateActuacion).toHaveBeenCalledTimes(1);
  return vi.mocked(updateActuacion).mock.calls[0][1] as Record<string, unknown>;
}

function expectNoSeguimiento(body: Record<string, unknown>): void {
  expect(body).not.toHaveProperty("solicita_carnet_manipulador");
  expect(body).not.toHaveProperty("telefono_contacto_solicitud_carnet");
  expect(body).not.toHaveProperty("faltas_notificacion_subsanadas");
}

describe("submitActuacionRow seguimiento PUT 2", () => {
  beforeEach(() => {
    vi.mocked(updateActuacion).mockClear();
  });

  it("Seguimiento en No sin tocar + editar observación → body sin campos de Seguimiento", async () => {
    const original = baseRow();
    const edited = baseRow({ observaciones_ejecucion: "nueva nota" });
    const body = await putBody(edited, original);
    expectNoSeguimiento(body);
    expect(body.observaciones_ejecucion).toBe("nueva nota");
  });

  it("Seguimiento en Sí sin tocar + editar rubro → body sin Seguimiento", async () => {
    const original = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 999-8888",
    });
    const edited = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 999-8888",
      rubro_nombre: "Carnicería",
    });
    const body = await putBody(edited, original);
    expectNoSeguimiento(body);
    expect(body.rubro_nombre).toBe("Carnicería");
  });

  it("hidratar seguimiento existente no cuenta como cambio", async () => {
    const original = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 123-4567",
      seguimiento: {
        solicita_carnet_manipulador: true,
        telefono_contacto_solicitud_carnet: "381 123-4567",
      },
    });
    const edited = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 123-4567",
      seguimiento: {
        solicita_carnet_manipulador: true,
        telefono_contacto_solicitud_carnet: "381 123-4567",
      },
      observaciones_ejecucion: "otra",
    });
    const body = await putBody(edited, original);
    expectNoSeguimiento(body);
  });

  it("cambiar Solicita carnet de Sí a No envía false y teléfono null", async () => {
    const original = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 999-8888",
    });
    const edited = baseRow({
      solicita_carnet_manipulador: false,
      telefono_contacto_solicitud_carnet: null,
    });
    const body = await putBody(edited, original);
    expect(body.solicita_carnet_manipulador).toBe(false);
    expect(body.telefono_contacto_solicitud_carnet).toBeNull();
    expect(body).not.toHaveProperty("faltas_notificacion_subsanadas");
  });

  it("cambiar de No a Sí envía Sí y teléfono", async () => {
    const original = baseRow();
    const edited = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 111-2222",
    });
    const body = await putBody(edited, original);
    expect(body.solicita_carnet_manipulador).toBe(true);
    expect(body.telefono_contacto_solicitud_carnet).toBe("381 111-2222");
  });

  it("cambiar solo teléfono cuando la respuesta es Sí envía seguimiento", async () => {
    const original = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 111-2222",
    });
    const edited = baseRow({
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "381 333-4444",
    });
    const body = await putBody(edited, original);
    expect(body.solicita_carnet_manipulador).toBe(true);
    expect(body.telefono_contacto_solicitud_carnet).toBe("381 333-4444");
  });

  it("cambiar Faltas subsanadas envía solo ese campo", async () => {
    const original = baseRow({
      ui_policy: subsPolicy,
      faltas_notificacion_subsanadas: false,
    });
    const edited = baseRow({
      ui_policy: subsPolicy,
      faltas_notificacion_subsanadas: true,
    });
    const body = await putBody(edited, original);
    expect(body.faltas_notificacion_subsanadas).toBe(true);
    expect(body).not.toHaveProperty("solicita_carnet_manipulador");
    expect(body).not.toHaveProperty("telefono_contacto_solicitud_carnet");
  });
});
