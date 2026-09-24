import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  actuacionActaChipsOnly,
  actuacionActasYTramiteAccessor,
  actuacionDocumentacionOrigenReinspeccionSegments,
} from "./actuacionDocumentacionVisual";

describe("actuacionDocumentacionVisual REINSPECCION_NOTIFICACION", () => {
  const row = {
    acta_inspeccion_num: "023544",
    acta_notificacion_num: "006789",
    acta_comprobacion_num: "034456",
    documentacion_contexto: {
      circuito: "REINSPECCION_NOTIFICACION",
      propia: {
        notificacion_plazo_dias: 5,
        notificacion_fecha_vencimiento: "2026-06-10",
      },
    },
    origen_reinspeccion_notificacion: {
      notificacion_acta_numero: "006789",
      notificacion_acta_anio: 2026,
      plazo_dias: 5,
      fecha_vencimiento: "2026-06-10",
    },
  } as IActuacionListItem;

  it("no muestra chip de notificación actual ni plazos/vencimientos", () => {
    const chips = actuacionActaChipsOnly(row);
    expect(chips).toContain("Inspección 023544");
    expect(chips).toContain("Comprobación 034456");
    expect(chips).not.toContain("Notificación 006789");
    expect(chips.join(" ")).not.toMatch(/Plazo|Vencimiento/);
  });

  it("muestra origen de reinspección sin plazo/vencimiento duplicados", () => {
    const origen = actuacionDocumentacionOrigenReinspeccionSegments(row);
    expect(origen.some((s) => s.includes("Reinspección por notificación"))).toBe(true);
    expect(origen.some((s) => s.includes("Notificación origen"))).toBe(true);
    expect(origen.join(" ")).not.toMatch(/Plazo origen|Vencimiento/);
  });

  it("accessor compacto para columna Actas y trámites", () => {
    const text = actuacionActasYTramiteAccessor(row);
    expect(text).toContain("Inspección 023544");
    expect(text).toContain("Comprobación 034456");
    expect(text).toContain("Notificación origen");
    expect(text).not.toContain("Notificación 006789 |");
    expect(text).not.toMatch(/Plazo|Vencimiento/);
  });
});
