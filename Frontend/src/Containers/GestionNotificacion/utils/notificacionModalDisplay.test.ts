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

  it("subtitulo usa número de acta de notificación, fecha y estado", () => {
    const sub = notificacionModalSubtitulo(row as never);
    expect(sub).toContain("Número de acta de notificación N.º 000890");
    expect(sub).toContain("Fecha: 2026-06-28");
    expect(sub).toContain("5 días restantes");
    expect(sub).not.toContain("Acta N.º");
  });
});
