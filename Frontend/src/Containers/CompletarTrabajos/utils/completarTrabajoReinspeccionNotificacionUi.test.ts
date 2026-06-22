import { describe, expect, it } from "vitest";

import {
  showActasEstandarEnCompletarTrabajo,
  showNotificacionEditableEnCompletarTrabajo,
  showNotificacionOrigenReadonlyEnCompletarTrabajo,
} from "./completarTrabajoReinspeccionNotificacionUi";
import { prefillOperativoReinspeccionNotificacion } from "./completarTrabajoReinspeccionNotificacionPrefill";
import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { tipoIniciadorDesdeCodigoApi } from "../../RutasTrabajo/planificacion/utils/iniciadorDisplay";

describe("completarTrabajoReinspeccionNotificacionUi", () => {
  it("REINSPECCION_NOTIFICACION oculta notificación editable y muestra origen readonly", () => {
    expect(showNotificacionEditableEnCompletarTrabajo("REINSPECCION_NOTIFICACION")).toBe(false);
    expect(showNotificacionOrigenReadonlyEnCompletarTrabajo("REINSPECCION_NOTIFICACION")).toBe(true);
    expect(showActasEstandarEnCompletarTrabajo("REINSPECCION_NOTIFICACION")).toBe(true);
  });

  it("otros tipos mantienen notificación editable", () => {
    expect(showNotificacionEditableEnCompletarTrabajo("RELEVAMIENTO")).toBe(true);
    expect(showNotificacionOrigenReadonlyEnCompletarTrabajo("RELEVAMIENTO")).toBe(false);
  });

  it("no expone enum crudo en label humano", () => {
    expect(tipoIniciadorDesdeCodigoApi("REINSPECCION_NOTIFICACION")).toBe("Reinspección por notificación");
  });
});

describe("prefillOperativoReinspeccionNotificacion actas estándar", () => {
  it("precarga comprobación/clausura/decomiso y limpia notificación editable", () => {
    const row = {
      calle: "C",
      acta_comprobacion_num: "111",
      comprobacion_motivo: "Motivo X",
      acta_clausura_num: "222",
      acta_decomiso_num: "333",
      decomiso_kilos_total: 5,
      acta_notificacion_num: "999",
      notificacion_motivo_1: "M1",
    } as ICompletarTrabajoPendienteRow;
    const pre = prefillOperativoReinspeccionNotificacion(row);
    expect(pre.actaComprobacion).toBe("111");
    expect(pre.comprobacionMotivo).toBe("Motivo X");
    expect(pre.actaClausura).toBe("222");
    expect(pre.actaDecomiso).toBe("333");
    expect(pre.decomisoKilos).toBe("5");
    expect(pre.actaNotificacion).toBe("");
    expect(pre.notifMotivosSeleccion).toEqual([]);
  });
});
