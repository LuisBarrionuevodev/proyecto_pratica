import { describe, expect, it } from "vitest";

import {
  MENSAJE_OT_CONSUMIDA_CARD,
  mensajeErrorGuardarOtPatch,
} from "./rutaOtAsignacionMessages";

describe("mensajeErrorGuardarOtPatch", () => {
  it("mapea validator orden_trabajo_ocupada_por_otro_flujo al mensaje de card", () => {
    const r = mensajeErrorGuardarOtPatch("otro texto", {
      validator: "orden_trabajo_ocupada_por_otro_flujo",
    });
    expect(r.otConsumida).toBe(true);
    expect(r.message).toBe(MENSAJE_OT_CONSUMIDA_CARD);
    expect(r.message).toContain("OT ya fue utilizada");
    expect(r.message).toContain("queda consumida");
  });

  it("usa detail del backend para otros errores", () => {
    const r = mensajeErrorGuardarOtPatch("La orden de trabajo ya está asociada a otro item activo", null);
    expect(r.otConsumida).toBe(false);
    expect(r.message).toContain("otro item activo");
  });

  it("fallback genérico sin detail", () => {
    const r = mensajeErrorGuardarOtPatch(null, null);
    expect(r.message).toBe("No se pudo guardar la OT");
  });
});
