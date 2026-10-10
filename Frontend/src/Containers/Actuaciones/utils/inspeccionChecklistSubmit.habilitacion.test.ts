import { describe, expect, it } from "vitest";

import {
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
});
