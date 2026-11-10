import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { submitActuacionRow } from "./submitActuacionRow";

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

const normalRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 91,
    orden_trabajo_numero: "004764",
    fecha_actuacion: "2026-05-10",
    tipo_actuacion: "INSPECCION",
    rubro_nombre: "Bar",
    inspector1: "García",
    inspector2: "López",
    calle: "San Martín",
    numero: "100",
    numero_tipo: "NUMERO",
    contribuyente: { apellido: "Pérez", nombre: "Juan" },
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    doc_nro: "20345678901",
    contraproducencia: null,
    acta_inspeccion_num: "42",
    can_edit_domicilio: false,
    can_edit_rubro: true,
    documentacion_contexto: { circuito: "DESCONOCIDO", propia: {} },
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

describe("HOTFIX V1.1-ACT-EDIT.1C submit domicilio sin reenviar identidad", () => {
  beforeEach(() => {
    mockedUpdateActuacion.mockClear();
  });

  it("Denuncia con contribuyente hidratado envía calle/número/tipo y no identidad", async () => {
    const original = normalRow({ ruta_item_id: 88 });
    const body = await putBody(
      normalRow({
        ruta_item_id: 88,
        calle: "Catamarca",
        numero: "250",
        numero_tipo: "ESQUINA",
      }),
      original
    );
    expect(body.calle).toBe("Catamarca");
    expect(body.numero).toBe("250");
    expect(body.numero_tipo).toBe("ESQUINA");
    expect(body).not.toHaveProperty("doc_nro");
    expect(body).not.toHaveProperty("contrib_apellido");
    expect(body).not.toHaveProperty("contrib_nombre");
    expect(body).not.toHaveProperty("limpiar_contribuyente");
  });

  it("Relevamiento con contribuyente existente envía domicilio sin reasignar por DNI", async () => {
    const original = normalRow({
      ruta_item_id: 120,
      domicilio_edit_blocked_reason:
        "La actuación proviene de una reinspección y el domicilio no puede modificarse.",
    });
    const body = await putBody(
      normalRow({
        ruta_item_id: 120,
        calle: "Maipú",
        numero: "501",
        domicilio_edit_blocked_reason: original.domicilio_edit_blocked_reason,
      }),
      original
    );
    expect(body.calle).toBe("Maipú");
    expect(body.numero).toBe("501");
    expect(body).not.toHaveProperty("doc_nro");
  });
});
