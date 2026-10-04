import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { formatActuacionExportDetalles } from "./formatActuacionExportDetalles";

function row(overrides: Partial<IActuacionListItem> = {}): IActuacionListItem {
  return {
    id: 1,
    orden_trabajo_numero: null,
    fecha_actuacion: null,
    rubro_nombre: null,
    inspector1: null,
    inspector2: null,
    inspector3: null,
    calle: null,
    numero: null,
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    tipo_actuacion: null,
    contraproducencia: null,
    acta_inspeccion_num: null,
    acta_notificacion_num: null,
    notificacion_motivo_1: null,
    notificacion_motivo_2: null,
    notificacion_motivo_3: null,
    acta_comprobacion_num: null,
    comprobacion_motivo: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    decomiso_kilos_total: null,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
    ...overrides,
  };
}

describe("formatActuacionExportDetalles", () => {
  it("usa — cuando faltan datos; no infiere No", () => {
    const text = formatActuacionExportDetalles(row(), { exposeTelefono: true });
    expect(text).toBe(
      "Habilitación: —\nCarnet de manipulador solicitado: —\nTeléfono de contacto: —"
    );
  });

  it("formatea habilitación y carnet desde datos persistidos", () => {
    const text = formatActuacionExportDetalles(
      row({
        items_acta_inspeccion: [
          { id: 6, codigo: "TIENE_HABILITACION", nombre: "Hab", valor_si_no: true },
        ],
        solicita_carnet_manipulador: false,
      }),
      { exposeTelefono: true }
    );
    expect(text).toContain("Habilitación: Sí");
    expect(text).toContain("Carnet de manipulador solicitado: No");
    expect(text).toContain("Teléfono de contacto: —");
  });

  it("teléfono solo si fue solicitado, existe y está autorizado", () => {
    const withPhone = formatActuacionExportDetalles(
      row({
        solicita_carnet_manipulador: true,
        telefono_contacto_solicitud_carnet: "3815551234",
      }),
      { exposeTelefono: true }
    );
    expect(withPhone).toContain("Teléfono de contacto: 3815551234");

    const hidden = formatActuacionExportDetalles(
      row({
        solicita_carnet_manipulador: true,
        telefono_contacto_solicitud_carnet: "3815551234",
      }),
      { exposeTelefono: false }
    );
    expect(hidden).toContain("Teléfono de contacto: —");
    expect(hidden).not.toContain("3815551234");
  });
});
