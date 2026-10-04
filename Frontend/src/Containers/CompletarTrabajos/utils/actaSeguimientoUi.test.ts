import { describe, expect, it } from "vitest";
import {
  faltasSubsanadasUiToBool,
  mostrarBloqueSolicitudCarnet,
  mostrarBloqueSubsanacionNotificacion,
  solicitaCarnetUiToBool,
} from "./actaSeguimientoUi";

describe("actaSeguimientoUi", () => {
  it("muestra bloques solo con flags del backend", () => {
    expect(mostrarBloqueSolicitudCarnet(null)).toBe(false);
    expect(
      mostrarBloqueSolicitudCarnet({
        recurso_logico: "actuacion",
        ancla_operativa: "ruta_item",
        orden_trabajo_y_fecha_readonly: true,
        inspectores_readonly: true,
        previas_visible: false,
        post_cierre: "",
        mostrar_solicitud_carnet_manipulador: true,
      })
    ).toBe(true);
    expect(
      mostrarBloqueSubsanacionNotificacion({
        recurso_logico: "actuacion",
        ancla_operativa: "ruta_item",
        orden_trabajo_y_fecha_readonly: true,
        inspectores_readonly: true,
        previas_visible: false,
        post_cierre: "",
        mostrar_subsanacion_notificacion: true,
      })
    ).toBe(true);
  });

  it("convierte valores si/no a boolean", () => {
    expect(solicitaCarnetUiToBool("si")).toBe(true);
    expect(solicitaCarnetUiToBool("no")).toBe(false);
    expect(faltasSubsanadasUiToBool("si")).toBe(true);
    expect(faltasSubsanadasUiToBool("no")).toBe(false);
  });
});
