import { describe, expect, it } from "vitest";

import {
  notificacionModalSubtitulo,
  notificacionModalTitulo,
} from "./notificacionModalDisplay";

describe("notificacionModalDisplay", () => {
  const row = {
    acta_notificacion_num: "000890",
    fecha_actuacion: "2026-06-28",
    dias_restantes: 5,
  } as const;

  it("titulo siempre Notificación detalle", () => {
    expect(notificacionModalTitulo("soloExpediente", false)).toBe("Notificación detalle");
    expect(notificacionModalTitulo("documental", true)).toBe("Notificación detalle");
    expect(notificacionModalTitulo("documental", false)).toBe("Notificación detalle");
  });

  it("subtitulo muestra solo número de acta de notificación", () => {
    const sub = notificacionModalSubtitulo(row as never);
    expect(sub).toBe("Número de acta de notificación N.º 000890");
    expect(sub).not.toContain("Fecha:");
    expect(sub).not.toContain("Estado:");
    expect(sub).not.toContain("días restantes");
    expect(sub).not.toContain("Acta N.º");
  });

  it("header no incluye fecha ni estado aunque la fila los tenga", () => {
    const sub = notificacionModalSubtitulo({
      acta_notificacion_num: "000001",
      fecha_actuacion: "2026-06-01",
      dias_restantes: 15,
    } as never);
    expect(sub).not.toContain("2026-06-01");
    expect(sub).not.toContain("15");
    expect(sub).toContain("000001");
  });
});
