import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { INSPECTOR_SELF_SERVICE_PUT_FORBIDDEN_KEYS } from "./buildInspectorSelfServiceUpdateBody";
import { submitActuacionRow } from "./submitActuacionRow";

const validateRow = vi.fn();
const updateActuacion = vi.fn();

vi.mock("../../../api/gridApi", () => ({
  validateRow: (...args: unknown[]) => validateRow(...args),
}));

vi.mock("../../../api/actuacionesApi", () => ({
  updateActuacion: (...args: unknown[]) => updateActuacion(...args),
}));

const baseRow = (overrides?: Partial<IActuacionListItem>): IActuacionListItem =>
  ({
    id: 7,
    orden_trabajo_numero: "100",
    orden_trabajo_id: 50,
    fecha_actuacion: "2026-06-01",
    tipo_actuacion: "Inspección",
    contraproducencia: "No",
    rubro_nombre: "Bar",
    calle: "Calle Vieja",
    numero: "1",
    inspector1: "A",
    inspector2: "B",
    inspectores: ["A", "B"],
    domicilio_id: 99,
    ruta_item_id: 12,
    iniciador_ruta_id: 3,
    ruta_trabajo_id: 4,
    actuacion_id: 7,
    ui_policy: {
      puede_editar_seguimiento: false,
      mostrar_solicitud_carnet_manipulador: false,
      mostrar_subsanacion_notificacion: false,
      puede_editar_datos_propios: true,
      puede_gestionar_fotos_propias: true,
    },
    ...overrides,
  }) as IActuacionListItem;

describe("submitActuacionRow inspector Mis trabajos", () => {
  beforeEach(() => {
    validateRow.mockReset();
    updateActuacion.mockReset();
    updateActuacion.mockResolvedValue(baseRow());
  });

  it("inspectorSelfService: omite validate-row, un PUT y body sin claves prohibidas", async () => {
    const row = baseRow({ nombre_local: "Local editado" });
    const result = await submitActuacionRow({
      id: 7,
      fullRow: row,
      originalRow: row,
      skipValidation: false,
      skipGridRowValidation: true,
      inspectorSelfService: true,
      skipUpdate: false,
    });
    expect(validateRow).not.toHaveBeenCalled();
    expect(updateActuacion).toHaveBeenCalledTimes(1);
    expect(result.ok).toBe(true);

    const [, body] = updateActuacion.mock.calls[0] as [number, Record<string, unknown>];
    expect(body.nombre_local).toBe("Local editado");
    expect(body.rubro_nombre).toBe("Bar");
    for (const key of INSPECTOR_SELF_SERVICE_PUT_FORBIDDEN_KEYS) {
      expect(body).not.toHaveProperty(key);
    }
    expect(body).not.toHaveProperty("inspectores");
  });

  it("inspectorSelfService: checklist JSON sin transformar en el PUT", async () => {
    const checklist = [
      { item_id: 1, estado: "BIEN" },
      { item_id: 2, estado: "BIEN" },
      { item_id: 6, valor_si_no: true },
    ];
    const row = baseRow({
      items_acta_inspeccion: checklist,
      acta_inspeccion_num: "000100",
    });
    await submitActuacionRow({
      id: 7,
      fullRow: row,
      originalRow: row,
      skipValidation: true,
      skipGridRowValidation: true,
      inspectorSelfService: true,
      inspeccionChecklistTouched: { items: true },
      inspeccionChecklistCatalog: [
        { id: 1, codigo: "TIENE_BANO", nombre: "Baño", tipo_respuesta: "ESTADO" },
        { id: 2, codigo: "TIENE_SALON", nombre: "Salón", tipo_respuesta: "ESTADO" },
        { id: 6, codigo: "TIENE_HABILITACION", nombre: "Tiene habilitación", tipo_respuesta: "SI_NO" },
      ],
      skipUpdate: false,
    });
    const [, body] = updateActuacion.mock.calls[0] as [number, Record<string, unknown>];
    expect(body.items_acta_inspeccion).toEqual(checklist);
  });

  it("inspectorSelfService: un solo inspector en fila no bloquea validación ni envía inspectores", async () => {
    const row = baseRow({
      inspector2: null,
      inspectores: ["A"],
      nombre_local: "Solo un inspector",
    });
    const result = await submitActuacionRow({
      id: 7,
      fullRow: row,
      originalRow: row,
      skipValidation: false,
      skipGridRowValidation: true,
      inspectorSelfService: true,
      skipUpdate: false,
    });
    expect(result.ok).toBe(true);
    const [, body] = updateActuacion.mock.calls[0] as [number, Record<string, unknown>];
    expect(body).not.toHaveProperty("inspectores");
  });

  it("Admin/Usuario: conserva payload con inspectores cuando corresponde", async () => {
    validateRow.mockResolvedValue({ ok: true, batch_id: "", row_id: "", errors: {} });
    const row = baseRow();
    await submitActuacionRow({
      id: 7,
      fullRow: row,
      originalRow: row,
      skipValidation: false,
      skipGridRowValidation: false,
      inspectorSelfService: false,
      skipUpdate: false,
    });
    expect(updateActuacion).toHaveBeenCalledTimes(1);
    const [, body] = updateActuacion.mock.calls[0] as [number, Record<string, unknown>];
    expect(body.inspectores).toEqual(["A", "B"]);
    expect(body.id).toBe(7);
  });
});
