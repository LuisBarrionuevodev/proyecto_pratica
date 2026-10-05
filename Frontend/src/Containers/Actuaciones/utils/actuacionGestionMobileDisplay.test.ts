import { describe, expect, it } from "vitest";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  actuacionGestionMobileDomicilio,
  actuacionGestionMobileEstado,
  actuacionGestionMobileIdentificador,
} from "./actuacionGestionMobileDisplay";

const row = {
  id: 9,
  orden_trabajo_numero: "000123",
  fecha_actuacion: "2026-10-01",
  tipo_actuacion: "INSPECCION",
  contraproducencia: null,
  calle: "San Martín",
  numero: "100",
  contrib_apellido: "Pérez",
  contrib_nombre: "Ana",
} as IActuacionListItem;

describe("actuacionGestionMobileDisplay", () => {
  it("identificador prioriza OT", () => {
    expect(actuacionGestionMobileIdentificador(row)).toMatch(/123/);
  });

  it("estado marca no editable", () => {
    expect(
      actuacionGestionMobileEstado({ ...row, actuacion_editable: false, motivo_bloqueo_edicion: "Cerrada" })
    ).toBe("Cerrada");
  });

  it("domicilio arma línea visible", () => {
    expect(actuacionGestionMobileDomicilio(row)).toContain("San Martín");
  });
});
