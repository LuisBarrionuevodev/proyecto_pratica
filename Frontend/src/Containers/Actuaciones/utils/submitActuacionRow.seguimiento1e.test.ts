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

const baseRow = (): IActuacionListItem =>
  ({
    id: 42,
    orden_trabajo_numero: "12345",
    fecha_actuacion: "2026-06-01",
    rubro_nombre: "Panadería",
    inspector1: "Inspector A",
    inspector2: null,
    inspector3: null,
    calle: "Mitre",
    numero: "100",
    tipo_actuacion: "Inspección",
    contraproducencia: "No",
    doc_nro: null,
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
    ui_policy: {
      mostrar_solicitud_carnet_manipulador: true,
      mostrar_subsanacion_notificacion: false,
      puede_editar_seguimiento: true,
    },
    solicita_carnet_manipulador: true,
    telefono_contacto_solicitud_carnet: "381 999-8888",
  }) as IActuacionListItem;

describe("submitActuacionRow seguimiento PUT 1E", () => {
  beforeEach(() => {
    vi.mocked(updateActuacion).mockClear();
  });

  it("incluye teléfono de seguimiento en el body del PUT", async () => {
    const row = baseRow();
    const result = await submitActuacionRow({
      id: 42,
      fullRow: row,
      originalRow: row,
      skipValidation: false,
      skipUpdate: false,
    });
    expect(result.ok).toBe(true);
    expect(updateActuacion).toHaveBeenCalledTimes(1);
    const body = vi.mocked(updateActuacion).mock.calls[0][1] as Record<string, unknown>;
    expect(body.solicita_carnet_manipulador).toBe(true);
    expect(body.telefono_contacto_solicitud_carnet).toBe("381 999-8888");
    expect(body.ui_policy).toBeUndefined();
    expect(body.seguimiento).toBeUndefined();
  });
});
