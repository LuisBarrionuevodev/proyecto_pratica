import { describe, expect, it } from "vitest";

import {
  checklistUxValueAt,
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
});
