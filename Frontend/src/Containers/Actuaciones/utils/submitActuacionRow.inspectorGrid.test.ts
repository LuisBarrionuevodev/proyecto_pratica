import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { submitActuacionRow } from "./submitActuacionRow";

const validateRow = vi.fn();
const updateActuacion = vi.fn();

vi.mock("../../../api/gridApi", () => ({
  validateRow: (...args: unknown[]) => validateRow(...args),
}));

vi.mock("../../../api/actuacionesApi", () => ({
  updateActuacion: (...args: unknown[]) => updateActuacion(...args),
}));

const baseRow = (): IActuacionListItem =>
  ({
    id: 7,
    orden_trabajo_numero: "100",
    fecha_actuacion: "2026-06-01",
    tipo_actuacion: "Inspección",
    contraproducencia: "No",
    rubro_nombre: "Bar",
    calle: "Calle",
    numero: "1",
    inspector1: "A",
    ui_policy: {
      puede_editar_seguimiento: false,
      mostrar_solicitud_carnet_manipulador: false,
      mostrar_subsanacion_notificacion: false,
      puede_editar_datos_propios: true,
      puede_gestionar_fotos_propias: true,
    },
  }) as IActuacionListItem;

describe("submitActuacionRow inspector Mis trabajos", () => {
  beforeEach(() => {
    validateRow.mockReset();
    updateActuacion.mockReset();
    updateActuacion.mockResolvedValue(baseRow());
  });

  it("skipGridRowValidation omite POST /grid/validate-row y ejecuta PUT", async () => {
    const row = baseRow();
    const result = await submitActuacionRow({
      id: 7,
      fullRow: row,
      originalRow: row,
      skipValidation: false,
      skipGridRowValidation: true,
      skipUpdate: false,
    });
    expect(validateRow).not.toHaveBeenCalled();
    expect(updateActuacion).toHaveBeenCalledTimes(1);
    expect(result.ok).toBe(true);
  });
});
