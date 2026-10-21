import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  ACTUACION_PUT_READ_ONLY_METADATA_KEYS,
  buildActuacionUpdatePayload,
} from "./buildActuacionUpdatePayload";

const relevamientoRowWithMetadata = (): Record<string, unknown> =>
  ({
    id: 10,
    orden_trabajo_numero: "000123",
    fecha_actuacion: "2026-06-01",
    tipo_actuacion: "INSPECCION",
    rubro_nombre: "Bar",
    nombre_local: "Local",
    calle: "San Martín",
    numero: "100",
    inspector1: "A",
    inspector2: "B",
    inspectores: ["A", "B"],
    actuacion_editable: true,
    actuacion_bloqueada_por_expediente: false,
    motivo_bloqueo_edicion: null,
    calle_cargada: "San Martín",
    calle_raw: "san martin",
    esquina_cargada: null,
    esquina_key: null,
    can_edit_rubro: true,
    rubro_edit_blocked_reason: null,
    carga_solo_comprobacion: false,
    realizo_nueva_inspeccion: null,
    expediente_numero: "99",
    expediente_anio: 2024,
    oficio_numero: "1",
    oficio_anio: 2024,
    oficio_causa: "X",
    ui_policy: { puede_editar_seguimiento: false },
    documentacion_contexto: { circuito: "DESCONOCIDO", propia: {} },
  }) as IActuacionListItem;

describe("buildActuacionUpdatePayload", () => {
  it("relevamiento: omite metadata de lectura y documental", () => {
    const source = relevamientoRowWithMetadata();
    const payload = buildActuacionUpdatePayload(source, { inspectorSelfService: false });

    for (const key of ACTUACION_PUT_READ_ONLY_METADATA_KEYS) {
      expect(payload).not.toHaveProperty(key);
    }
    expect(payload.rubro_nombre).toBe("Bar");
    expect(payload.calle).toBe("San Martín");
    expect(payload.inspectores).toEqual(["A", "B"]);
  });

  it("Admin conserva campos editables del contrato grid", () => {
    const payload = buildActuacionUpdatePayload(relevamientoRowWithMetadata());
    expect(payload.id).toBe(10);
    expect(payload.fecha_actuacion).toBe("2026-06-01");
    expect(payload.orden_trabajo_numero).toBe("000123");
  });

  it("Inspector: no envía inspectores ni campos operativos restringidos", () => {
    const payload = buildActuacionUpdatePayload(
      { ...relevamientoRowWithMetadata(), nombre_local: "Editado" },
      { inspectorSelfService: true }
    );
    expect(payload.nombre_local).toBe("Editado");
    expect(payload).not.toHaveProperty("inspectores");
    expect(payload).not.toHaveProperty("inspector1");
    expect(payload).not.toHaveProperty("id");
    expect(payload).not.toHaveProperty("fecha_actuacion");
    expect(payload).not.toHaveProperty("orden_trabajo_numero");
    expect(payload).not.toHaveProperty("actuacion_editable");
  });

  it("payload Admin no incluye ninguna clave de solo lectura conocida", () => {
    const payload = buildActuacionUpdatePayload(relevamientoRowWithMetadata());
    const payloadKeys = new Set(Object.keys(payload));
    for (const key of ACTUACION_PUT_READ_ONLY_METADATA_KEYS) {
      expect(payloadKeys.has(key)).toBe(false);
    }
  });
});
