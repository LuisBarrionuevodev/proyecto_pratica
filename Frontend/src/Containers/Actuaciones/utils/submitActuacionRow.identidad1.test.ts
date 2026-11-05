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

const baseRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 387,
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
    doc_nro: "27410601538",
    contrib_apellido: "Chávez",
    contrib_nombre: "Erika del Valle",
    razon_social: null,
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
    observaciones_ejecucion: "original",
    ui_policy: {
      mostrar_solicitud_carnet_manipulador: true,
      mostrar_subsanacion_notificacion: false,
      puede_editar_seguimiento: true,
    },
    solicita_carnet_manipulador: false,
    telefono_contacto_solicitud_carnet: null,
    ...overrides,
  }) as IActuacionListItem;

async function putBody(
  fullRow: IActuacionListItem,
  originalRow: IActuacionListItem,
  extra?: { contribuyenteIdentityTouched?: Record<string, boolean> }
): Promise<Record<string, unknown>> {
  const result = await submitActuacionRow({
    id: 387,
    fullRow,
    originalRow,
    skipValidation: true,
    skipUpdate: false,
    contribuyenteIdentityTouched: extra?.contribuyenteIdentityTouched,
  });
  expect(result.ok).toBe(true);
  expect(updateActuacion).toHaveBeenCalledTimes(1);
  return vi.mocked(updateActuacion).mock.calls[0][1] as Record<string, unknown>;
}

describe("submitActuacionRow identidad PUT 1", () => {
  beforeEach(() => {
    vi.mocked(updateActuacion).mockClear();
  });

  it("editar solo observaciones no envía identidad ni limpiar_contribuyente", async () => {
    const original = baseRow();
    const edited = baseRow({ observaciones_ejecucion: "nueva nota" });
    const body = await putBody(edited, original);
    expect(body).not.toHaveProperty("doc_nro");
    expect(body).not.toHaveProperty("contrib_apellido");
    expect(body).not.toHaveProperty("contrib_nombre");
    expect(body).not.toHaveProperty("razon_social");
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("solicita_carnet_manipulador");
    expect(body.observaciones_ejecucion).toBe("nueva nota");
  });

  it("editar solo rubro no envía identidad", async () => {
    const original = baseRow();
    const body = await putBody(baseRow({ rubro_nombre: "Carnicería" }), original);
    expect(body).not.toHaveProperty("doc_nro");
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body.rubro_nombre).toBe("Carnicería");
  });

  it("editar solo número de acta no envía identidad ni limpiar_contribuyente", async () => {
    const original = baseRow();
    const body = await putBody(baseRow({ acta_inspeccion_num: "200" }), original);
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
    expect(body.acta_inspeccion_num).toBeTruthy();
  });

  it("editar solo condiciones de inspección no envía limpiar_contribuyente", async () => {
    const original = baseRow({
      items_acta_inspeccion: [{ id: 1, codigo: "TIENE_BANO", estado: "BIEN" }],
    });
    const result = await submitActuacionRow({
      id: 387,
      fullRow: baseRow({
        items_acta_inspeccion: [{ item_id: 1, estado: "OBSERVADO" }],
      }),
      originalRow: original,
      inspeccionChecklistTouched: { items: true },
      skipValidation: true,
      skipUpdate: false,
    });
    expect(result.ok).toBe(true);
    const body = vi.mocked(updateActuacion).mock.calls[0][1] as Record<string, unknown>;
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
    expect(body.items_acta_inspeccion).toEqual([{ item_id: 1, estado: "OBSERVADO" }]);
  });

  it("editar solo seguimiento/carnet no envía limpiar_contribuyente", async () => {
    const original = baseRow();
    const body = await putBody(
      baseRow({
        solicita_carnet_manipulador: true,
        telefono_contacto_solicitud_carnet: "3515551234",
      }),
      original
    );
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
    expect(body.solicita_carnet_manipulador).toBe(true);
  });

  it("editar solo apellido envía el grupo completo y coherente", async () => {
    const original = baseRow();
    const body = await putBody(baseRow({ contrib_apellido: "Gómez" }), original, {
      contribuyenteIdentityTouched: { contrib_apellido: true },
    });
    expect(body.doc_nro).toBe("27410601538");
    expect(body.contrib_apellido).toBe("Gómez");
    expect(body.contrib_nombre).toBe("Erika del Valle");
    expect(body.razon_social).toBeNull();
    expect(body).not.toHaveProperty("limpiar_contribuyente");
  });

  it("vaciar identidad sin confirmación no envía limpiar_contribuyente", async () => {
    const original = baseRow();
    const emptied = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      razon_social: null,
    });
    const body = await putBody(emptied, original, {
      contribuyenteIdentityTouched: { contrib_apellido: true, doc_nro: true },
    });
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
  });

  it("guardar sin cambios no envía limpiar_contribuyente", async () => {
    const original = baseRow();
    const body = await putBody(original, original);
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
  });

  it("un row interno con limpiar_contribuyente: true no lo manda en el PUT", async () => {
    const original = baseRow();
    const forced = baseRow({ limpiar_contribuyente: true });
    const body = await putBody(forced, original);
    expect(body).not.toHaveProperty("limpiar_contribuyente");
  });

  it("sin contribuyente asociado permite guardar cambios comunes", async () => {
    const original = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      razon_social: null,
    });
    const body = await putBody(
      baseRow({
        doc_nro: null,
        contrib_apellido: null,
        contrib_nombre: null,
        observaciones_ejecucion: "ok",
      }),
      original
    );
    expect(body).not.toHaveProperty("limpiar_contribuyente");
    expect(body).not.toHaveProperty("doc_nro");
    expect(body.observaciones_ejecucion).toBe("ok");
  });

  it("regresión seguimiento: sin contribuyente y sin tocar carnet no envía seguimiento", async () => {
    const original = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      solicita_carnet_manipulador: false,
    });
    const body = await putBody(
      baseRow({
        doc_nro: null,
        contrib_apellido: null,
        contrib_nombre: null,
        solicita_carnet_manipulador: false,
        rubro_nombre: "Kiosco",
      }),
      original
    );
    expect(body).not.toHaveProperty("solicita_carnet_manipulador");
    expect(body).not.toHaveProperty("telefono_contacto_solicitud_carnet");
    expect(body).not.toHaveProperty("limpiar_contribuyente");
  });
});
