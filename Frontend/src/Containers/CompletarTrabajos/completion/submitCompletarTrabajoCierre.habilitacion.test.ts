import { describe, expect, it, vi, beforeEach } from "vitest";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";
import { itemsActaInspeccionWriteFromEstados } from "../../Actuaciones/utils/inspeccionChecklistSubmit";
import { postCompletarTrabajoCerrar } from "../../../api/completarTrabajoApi";
import { submitCompletarTrabajoCierreFromRow } from "./submitCompletarTrabajoCierre";

vi.mock("../../../api/completarTrabajoApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/completarTrabajoApi")>();
  return {
    ...mod,
    postCompletarTrabajoCerrar: vi.fn().mockResolvedValue({ item: { ruta_item_id: 121 } }),
  };
});

const catalog: IItemActaInspeccionCatalogItem[] = [
  { id: 1, codigo: "BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" },
  { id: 2, codigo: "COCINA", nombre: "Cocina", orden: 2, tipo_respuesta: "ESTADO" },
  { id: 3, codigo: "DEPOSITO", nombre: "Depósito", orden: 3, tipo_respuesta: "ESTADO" },
  {
    id: 12,
    codigo: "TIENE_HABILITACION",
    nombre: "Tiene habilitación",
    orden: 6,
    tipo_respuesta: "SI_NO",
  },
];

const row = { ruta_item_id: 121 } as ICompletarTrabajoPendienteRow;

describe("submitCompletarTrabajoCierre — serialización habilitación en POST", () => {
  beforeEach(() => {
    vi.mocked(postCompletarTrabajoCerrar).mockClear();
  });

  it("envía valor_si_no true cuando el operador eligió Sí", async () => {
    const estados = {
      1: "BIEN" as const,
      2: "BIEN" as const,
      3: "OBSERVADO" as const,
      12: "SI" as const,
    };
    const items = itemsActaInspeccionWriteFromEstados(estados, catalog);

    await submitCompletarTrabajoCierreFromRow(row, {
      contraproducencia: "",
      acta_inspeccion_num: "000456",
      items_acta_inspeccion: items,
    });

    expect(postCompletarTrabajoCerrar).toHaveBeenCalledTimes(1);
    const [, body] = vi.mocked(postCompletarTrabajoCerrar).mock.calls[0]!;
    expect(body.items_acta_inspeccion).toEqual(
      expect.arrayContaining([
        { item_id: 1, estado: "BIEN" },
        { item_id: 2, estado: "BIEN" },
        { item_id: 3, estado: "OBSERVADO" },
        expect.objectContaining({ item_id: 12, valor_si_no: true }),
      ])
    );
    expect(body.items_acta_inspeccion).toHaveLength(4);
  });

  it("envía valor_si_no false cuando el operador eligió No", async () => {
    const estados = {
      1: "BIEN" as const,
      12: "NO" as const,
    };
    const items = itemsActaInspeccionWriteFromEstados(estados, catalog);

    await submitCompletarTrabajoCierreFromRow(row, {
      contraproducencia: "",
      acta_inspeccion_num: "000456",
      items_acta_inspeccion: items,
    });

    const [, body] = vi.mocked(postCompletarTrabajoCerrar).mock.calls[0]!;
    expect(body.items_acta_inspeccion).toEqual(
      expect.arrayContaining([
        { item_id: 1, estado: "BIEN" },
        expect.objectContaining({ item_id: 12, valor_si_no: false }),
      ])
    );
  });

  it("sin habilitación respondida no inventa valor_si_no en el body", async () => {
    const estados = {
      1: "BIEN" as const,
      2: "BIEN" as const,
      3: "OBSERVADO" as const,
      12: "NONE" as const,
    };
    const items = itemsActaInspeccionWriteFromEstados(estados, catalog);

    await submitCompletarTrabajoCierreFromRow(row, {
      contraproducencia: "",
      acta_inspeccion_num: "000456",
      items_acta_inspeccion: items,
    });

    const [, body] = vi.mocked(postCompletarTrabajoCerrar).mock.calls[0]!;
    expect(body.items_acta_inspeccion).toEqual([
      { item_id: 1, estado: "BIEN" },
      { item_id: 2, estado: "BIEN" },
      { item_id: 3, estado: "OBSERVADO" },
    ]);
    expect(body.items_acta_inspeccion?.some((i) => "valor_si_no" in i)).toBe(false);
  });
});
