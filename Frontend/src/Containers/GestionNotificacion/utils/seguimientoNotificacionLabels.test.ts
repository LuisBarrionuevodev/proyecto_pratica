import { describe, expect, it } from "vitest";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import {
  cierreNotificacionEstadoTramiteLabel,
  cierreNotificacionFilas,
  cierreNotificacionResultadoFaltasLabel,
  seguimientoNotificacionChipLabel,
  seguimientoNotificacionDeFila,
} from "./seguimientoNotificacionLabels";

describe("seguimientoNotificacionLabels", () => {
  it("tabla: sin reinspección muestra chip compacto", () => {
    expect(seguimientoNotificacionChipLabel("SIN_REINSPECCION")).toBe("Sin reinspección registrada");
  });

  it("tabla: reinspección sin resultado no inventa faltas", () => {
    expect(seguimientoNotificacionChipLabel("REINSPECCION_REALIZADA_SIN_RESULTADO")).toBe(
      "Reinspección realizada"
    );
    const seg = seguimientoNotificacionDeFila({
      id: 1,
      seguimiento_notificacion: {
        estado: "REINSPECCION_REALIZADA_SIN_RESULTADO",
        actuacion_id: 9,
        fecha_reinspeccion: "2026-04-10",
        acta_comprobacion_num: "REIN03",
        inspectores_texto: "Pérez",
        faltas_subsanadas: null,
      },
    } as IActuacionesPendientesItem);
    expect(cierreNotificacionResultadoFaltasLabel(seg)).toBe("No informado");
    expect(cierreNotificacionEstadoTramiteLabel(seg)).toBe(
      "Reinspección realizada · resultado no informado"
    );
  });

  it("tabla: faltas subsanadas y no subsanadas", () => {
    expect(seguimientoNotificacionChipLabel("FALTAS_SUBSANADAS")).toBe("Faltas subsanadas");
    expect(seguimientoNotificacionChipLabel("FALTAS_NO_SUBSANADAS")).toBe("Faltas no subsanadas");
  });

  it("modal cierre: sin reinspección usa guión en resultado de faltas", () => {
    const filas = cierreNotificacionFilas({
      id: 1,
      source_type: "NOTIFICACION",
      seguimiento_notificacion: {
        estado: "SIN_REINSPECCION",
        actuacion_id: null,
        fecha_reinspeccion: null,
        acta_comprobacion_num: null,
        inspectores_texto: null,
        faltas_subsanadas: null,
      },
    } as IActuacionesPendientesItem);
    expect(filas.find((f) => f.etiqueta === "Estado del trámite")?.valor).toBe(
      "Sin reinspección registrada"
    );
    expect(filas.find((f) => f.etiqueta === "Resultado de las faltas")?.valor).toBe("—");
    expect(filas.find((f) => f.etiqueta === "Fecha de reinspección")?.valor).toBe("—");
  });

  it("modal cierre: no usa segunda inspección como etiqueta", () => {
    const filas = cierreNotificacionFilas({
      id: 1,
      seguimiento_notificacion: {
        estado: "FALTAS_SUBSANADAS",
        actuacion_id: 2,
        fecha_reinspeccion: "2026-04-10",
        acta_comprobacion_num: "99",
        inspectores_texto: "Gómez",
        faltas_subsanadas: true,
      },
    } as IActuacionesPendientesItem);
    const texto = filas.map((f) => `${f.etiqueta} ${f.valor}`).join(" ");
    expect(texto).toContain("Fecha de reinspección");
    expect(texto).not.toContain("segunda inspección");
    expect(filas.find((f) => f.etiqueta === "Resultado de las faltas")?.valor).toBe("Subsanadas");
  });
});
