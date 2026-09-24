import { describe, expect, it } from "vitest";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { prefillOperativoReinspeccionNotificacion } from "./completarTrabajoReinspeccionNotificacionPrefill";

describe("prefillOperativoReinspeccionNotificacion", () => {
  it("precarga domicilio y titular sin acta/motivos de notificación", () => {
    const row = {
      tipo_iniciador: "REINSPECCION_NOTIFICACION",
      calle: "San Martín",
      numero: "100",
      rubro_nombre: "Panadería",
      doc_nro: "20123456789",
      contrib_apellido: "Pérez",
      contrib_nombre: "Ana",
      razon_social: "",
      nombre_local: "La Esquina",
      domicilio_texto: "San Martín 100",
      acta_inspeccion_num: "123",
      acta_notificacion_num: "456",
      notificacion_motivo_1: "Motivo A",
    } as ICompletarTrabajoPendienteRow;

    const pre = prefillOperativoReinspeccionNotificacion(row);
    expect(pre.calle).toBe("San Martín");
    expect(pre.numero).toBe("100");
    expect(pre.rubroNombre).toBe("Panadería");
    expect(pre.contribApellido).toBe("Pérez");
    expect(pre.nombreLocal).toBe("La Esquina");
    expect(pre.actaInspeccion).toBe("123");
    expect(pre.actaComprobacion).toBe("");
    expect(pre.actaNotificacion).toBe("");
    expect(pre.notifMotivosSeleccion).toEqual([]);
  });
});
