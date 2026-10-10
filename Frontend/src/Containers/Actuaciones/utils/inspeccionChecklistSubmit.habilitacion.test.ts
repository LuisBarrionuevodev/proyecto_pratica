import { describe, expect, it } from "vitest";

import {
  checklistUxValueAt,
  itemsActaInspeccionWriteFromEstados,
  MSG_TIENE_HABILITACION_REQUERIDA,
  validateTieneHabilitacionObligatoria,
} from "./inspeccionChecklistSubmit";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";

const catalog: IItemActaInspeccionCatalogItem[] = [
  { id: 6, codigo: "TIENE_HABILITACION", nombre: "Tiene habilitación", orden: 6, tipo_respuesta: "SI_NO" },
];

describe("validateTieneHabilitacionObligatoria", () => {
  it("rechaza NONE", () => {
    expect(validateTieneHabilitacionObligatoria({ 6: "NONE" }, catalog)).toBe(
      MSG_TIENE_HABILITACION_REQUERIDA
    );
  });

  it("acepta SÍ y No", () => {
    expect(validateTieneHabilitacionObligatoria({ 6: "SI" }, catalog)).toBeNull();
    expect(validateTieneHabilitacionObligatoria({ 6: "NO" }, catalog)).toBeNull();
  });

  it("lee estado con clave string (serialización)", () => {
    const estados = { "6": "SI" } as unknown as Record<number, "SI">;
    expect(checklistUxValueAt(estados, 6)).toBe("SI");
    expect(validateTieneHabilitacionObligatoria(estados, catalog)).toBeNull();
  });

  it("itemsActaInspeccionWriteFromEstados incluye SI con clave string", () => {
    const estados = { "6": "SI", 1: "BIEN" } as Record<number, "SI" | "BIEN">;
    const fullCatalog = [
      { id: 1, codigo: "BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" as const },
      ...catalog,
    ];
    expect(itemsActaInspeccionWriteFromEstados(estados, fullCatalog)).toEqual(
      expect.arrayContaining([
        { item_id: 6, valor_si_no: true },
        { item_id: 1, estado: "BIEN" },
      ])
    );
  });
});
