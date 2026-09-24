import { describe, expect, it } from "vitest";

import {
  ACTUACION_VALIDATION_FIELD_LABELS,
  getActuacionValidationFieldLabel,
} from "./actuacionValidationFieldLabels";

describe("actuacionValidationFieldLabels", () => {
  it("expone labels de actas con N.º", () => {
    expect(getActuacionValidationFieldLabel("acta_inspeccion_num")).toBe("N.º de acta de inspección");
    expect(getActuacionValidationFieldLabel("acta_comprobacion_num")).toBe("N.º de acta de comprobación");
    expect(getActuacionValidationFieldLabel("acta_notificacion_num")).toBe("N.º de acta de notificación");
    expect(getActuacionValidationFieldLabel("acta_clausura_num")).toBe("N.º de acta de clausura");
    expect(getActuacionValidationFieldLabel("acta_decomiso_num")).toBe("N.º de acta de decomiso");
  });

  it("incluye motivos e inspectores", () => {
    expect(ACTUACION_VALIDATION_FIELD_LABELS.comprobacion_motivo).toBe("Motivo de comprobación");
    expect(ACTUACION_VALIDATION_FIELD_LABELS.notificacion_motivo_1).toBe("Motivo de notificación");
    expect(ACTUACION_VALIDATION_FIELD_LABELS.inspectores).toBe("Inspectores");
  });

  it("devuelve la clave si no hay label", () => {
    expect(getActuacionValidationFieldLabel("campo_desconocido")).toBe("campo_desconocido");
  });
});
