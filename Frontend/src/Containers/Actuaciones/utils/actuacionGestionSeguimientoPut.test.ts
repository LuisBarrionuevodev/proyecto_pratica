import { describe, expect, it } from "vitest";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  applyGestionSeguimientoDraftToRow,
  prepareActuacionGestionModalRow,
  stripActuacionRowForListStorage,
  buildGestionSeguimientoPutFields,
  stripGestionSeguimientoDisallowedFromPut,
} from "./actuacionGestionSeguimientoPut";

const baseRow = (): IActuacionListItem =>
  ({
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-06-01",
    rubro_nombre: "X",
    inspector1: null,
    inspector2: null,
    inspector3: null,
    calle: "A",
    numero: "1",
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    acta_inspeccion_num: "000100",
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
    notificacion_previa_num: null,
    comprobacion_previa_num: null,
    solicita_carnet_manipulador: true,
    telefono_contacto_solicitud_carnet: "351",
    faltas_notificacion_subsanadas: true,
  }) as IActuacionListItem;

describe("actuacionGestionSeguimientoPut", () => {
  it("strip omite seguimiento cuando ui_policy no habilita bloques", () => {
    const row = baseRow();
    const stripped = stripGestionSeguimientoDisallowedFromPut(row);
    expect(stripped.solicita_carnet_manipulador).toBeUndefined();
    expect(stripped.telefono_contacto_solicitud_carnet).toBeUndefined();
    expect(stripped.faltas_notificacion_subsanadas).toBeUndefined();
  });

  it("strip conserva solo campos permitidos por ui_policy", () => {
    const row = {
      ...baseRow(),
      ui_policy: {
        mostrar_solicitud_carnet_manipulador: true,
        mostrar_subsanacion_notificacion: false,
        puede_editar_seguimiento: true,
      },
    };
    const stripped = stripGestionSeguimientoDisallowedFromPut(row);
    expect(stripped.solicita_carnet_manipulador).toBe(true);
    expect(stripped.telefono_contacto_solicitud_carnet).toBe("351");
    expect(stripped.faltas_notificacion_subsanadas).toBeUndefined();
  });

  it("prepareActuacionGestionModalRow precarga teléfono desde seguimiento", () => {
    const detail = {
      ...baseRow(),
      telefono_contacto_solicitud_carnet: null,
      ui_policy: {
        mostrar_solicitud_carnet_manipulador: true,
        mostrar_subsanacion_notificacion: false,
        puede_editar_seguimiento: true,
      },
      seguimiento: {
        solicita_carnet_manipulador: true,
        telefono_contacto_solicitud_carnet: "381 123-4567",
      },
    } as IActuacionListItem;
    const row = prepareActuacionGestionModalRow(detail);
    expect(row.telefono_contacto_solicitud_carnet).toBe("381 123-4567");
  });

  it("stripActuacionRowForListStorage omite teléfono y metadatos de detalle", () => {
    const row = {
      ...baseRow(),
      telefono_contacto_solicitud_carnet: "secret",
      ui_policy: { mostrar_solicitud_carnet_manipulador: true },
      seguimiento: { telefono_contacto_solicitud_carnet: "secret" },
    } as IActuacionListItem;
    const stripped = stripActuacionRowForListStorage(row);
    expect(stripped.telefono_contacto_solicitud_carnet).toBeNull();
    expect(stripped.ui_policy).toBeUndefined();
    expect(stripped.seguimiento).toBeUndefined();
  });

  it("buildGestionSeguimientoPutFields incluye teléfono con policy explícita", () => {
    const row = {
      ...baseRow(),
      ui_policy: {
        mostrar_solicitud_carnet_manipulador: true,
        mostrar_subsanacion_notificacion: false,
        puede_editar_seguimiento: true,
      },
    };
    const fields = buildGestionSeguimientoPutFields(row, row.ui_policy);
    expect(fields.telefono_contacto_solicitud_carnet).toBe("351");
    const stripped = stripGestionSeguimientoDisallowedFromPut(
      { ...row, ui_policy: undefined },
      row.ui_policy
    );
    expect(stripped.telefono_contacto_solicitud_carnet).toBe("351");
  });

  it("applyGestionSeguimientoDraftToRow respeta policy", () => {
    const row = {
      ...baseRow(),
      ui_policy: {
        mostrar_solicitud_carnet_manipulador: false,
        mostrar_subsanacion_notificacion: true,
        puede_editar_seguimiento: true,
      },
    };
    const out = applyGestionSeguimientoDraftToRow(row, {
      solicitaCarnet: "si",
      telefonoCarnet: "999",
      faltasSubsanadas: "no",
    });
    expect(out.solicita_carnet_manipulador).toBe(true);
    expect(out.faltas_notificacion_subsanadas).toBe(false);
  });
});
