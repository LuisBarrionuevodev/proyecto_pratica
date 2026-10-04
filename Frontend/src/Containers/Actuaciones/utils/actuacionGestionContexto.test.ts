import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  formatGestionContribuyenteNombre,
  formatGestionDomicilioLinea,
  formatGestionRubroNombre,
  gestionContextoDisplayValue,
  GESTION_SIN_DATOS_LABEL,
} from "./actuacionGestionContexto";
import { validateGestionSeguimientoFields } from "./actuacionGestionSeguimientoPut";

const base: IActuacionListItem = {
  id: 1,
  orden_trabajo_numero: "1",
  fecha_actuacion: "2026-01-01",
  rubro_nombre: null,
  inspector1: null,
  inspector2: null,
  inspector3: null,
  calle: null,
  numero: null,
  tipo_actuacion: null,
  contraproducencia: null,
  doc_nro: null,
  contrib_apellido: null,
  contrib_nombre: null,
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
};

describe("actuacionGestionContexto", () => {
  it("usa objetos anidados del detalle autorizado", () => {
    const row: IActuacionListItem = {
      ...base,
      domicilio: { calle: "Mitre", numero: "100", esquina: "Junín" },
      rubro: { nombre: "Panadería" },
      contribuyente: { apellido: "Gómez", nombre: "Ana" },
    };
    expect(formatGestionDomicilioLinea(row)).toBe("Mitre 100 Junín");
    expect(formatGestionRubroNombre(row)).toBe("Panadería");
    expect(formatGestionContribuyenteNombre(row)).toBe("Gómez Ana");
  });

  it("sin datos históricos muestra etiqueta Sin datos registrados", () => {
    expect(gestionContextoDisplayValue(formatGestionDomicilioLinea(base))).toBe(
      GESTION_SIN_DATOS_LABEL
    );
  });
});

describe("validateGestionSeguimientoFields", () => {
  it("Sí sin teléfono devuelve error", () => {
    const errors = validateGestionSeguimientoFields({
      ...base,
      ui_policy: {
        mostrar_solicitud_carnet_manipulador: true,
        mostrar_subsanacion_notificacion: false,
        puede_editar_seguimiento: true,
      },
      solicita_carnet_manipulador: true,
      telefono_contacto_solicitud_carnet: "",
    });
    expect(errors.telefono_contacto_solicitud_carnet).toBeTruthy();
  });

  it("No no exige teléfono", () => {
    const errors = validateGestionSeguimientoFields({
      ...base,
      ui_policy: {
        mostrar_solicitud_carnet_manipulador: true,
        mostrar_subsanacion_notificacion: false,
        puede_editar_seguimiento: true,
      },
      solicita_carnet_manipulador: false,
      telefono_contacto_solicitud_carnet: null,
    });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});
