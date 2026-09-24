import { describe, expect, it } from "vitest";

import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";
import {
  dedupeNotificacionHistorialRows,
  notificacionHistorialRowKey,
} from "./dedupeNotificacionHistorialRows";

describe("dedupeNotificacionHistorialRows", () => {
  it("conserva una fila por notificacion_id prefiriendo INSPECCION", () => {
    const origen = {
      id: 10,
      notificacion_id: 99,
      tipo_actuacion: "INSPECCION",
      acta_notificacion_num: "000111",
    } as IActuacionesPendientesItem;
    const rein = {
      id: 20,
      notificacion_id: 99,
      tipo_actuacion: "REINSPECCION",
    } as IActuacionesPendientesItem;
    const out = dedupeNotificacionHistorialRows([rein, origen]);
    expect(out).toHaveLength(1);
    expect(out[0].id).toBe(10);
  });

  it("getRowId estable por notificacion_id", () => {
    const row = { id: 5, notificacion_id: 42 } as IActuacionesPendientesItem;
    expect(notificacionHistorialRowKey(row)).toBe("noti-42");
  });
});
