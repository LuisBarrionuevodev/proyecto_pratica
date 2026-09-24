import { describe, expect, it } from "vitest";

import {
  completarTrabajoHeaderSubtitulo,
  completarTrabajoHeaderTitulo,
  completarTrabajoShowDomicilioEnDetalle,
} from "./completarTrabajoModalDisplay";

describe("completarTrabajoModalDisplay", () => {
  it("header titulo usa tipo de iniciador sin prefijo", () => {
    expect(completarTrabajoHeaderTitulo("REINSPECCION_OFICIO")).toBe("Reinspección por oficio");
    expect(completarTrabajoHeaderTitulo("DENUNCIA")).toBe("Denuncia");
  });

  it("header subtitulo muestra fecha", () => {
    expect(completarTrabajoHeaderSubtitulo("2026-06-28")).toBe("Fecha: 2026-06-28");
  });

  it("domicilio en detalle solo cuando no es editable abajo", () => {
    expect(completarTrabajoShowDomicilioEnDetalle("REINSPECCION_OFICIO")).toBe(true);
    expect(completarTrabajoShowDomicilioEnDetalle("REINSPECCION_NOTIFICACION")).toBe(true);
    expect(completarTrabajoShowDomicilioEnDetalle("RELEVAMIENTO")).toBe(false);
    expect(completarTrabajoShowDomicilioEnDetalle("DENUNCIA")).toBe(false);
  });
});
