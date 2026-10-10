import { describe, expect, it } from "vitest";

import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";
import {
  itemsActaInspeccionWriteFromEstados,
  MSG_TIENE_HABILITACION_REQUERIDA,
  planChecklistHydration,
  validateTieneHabilitacionObligatoria,
} from "../../Actuaciones/utils/inspeccionChecklistSubmit";
import { MENSAJE_VALIDACION_LOCAL } from "../../Actuaciones/utils/actuacionSaveFeedback";
import { actuacionCompletarTrabajoValidationContext } from "../../Actuaciones/validations/actuacionFormValidation";
import { mergeCompletarTrabajoSubmitValidation } from "./completarTrabajoSubmitValidation";
import { checklistWriteFromEstados } from "./completarTrabajoVerificarInformarPrefill";

const catalogEnvA: IItemActaInspeccionCatalogItem[] = [
  { id: 1, codigo: "BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" },
  { id: 6, codigo: "TIENE_HABILITACION", nombre: "Tiene habilitación", orden: 6, tipo_respuesta: "SI_NO" },
];

const catalogEnvB: IItemActaInspeccionCatalogItem[] = [
  { id: 1, codigo: "BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" },
  { id: 12, codigo: "TIENE_HABILITACION", nombre: "Tiene habilitación", orden: 6, tipo_respuesta: "SI_NO" },
];

const formBase = {
  contraproducencia: "",
  calle: "San Martín",
  numero: "100",
  rubroNombre: "Carnicería",
  doc_nro: "12345678",
  contrib_apellido: "Pérez",
  contrib_nombre: "Juan",
  razon_social: null as string | null,
  nombre_local: "",
  fecha_actuacion: "2026-05-10",
  tipo_actuacion: "INSPECCION",
  acta_inspeccion_num: "12345",
  acta_comprobacion_num: "",
  comprobacion_motivo: "",
  acta_notificacion_num: "",
  notificacion_motivo_1: null as string | null,
  notificacion_motivo_2: null as string | null,
  notificacion_motivo_3: null as string | null,
  acta_clausura_num: "",
  acta_decomiso_num: "",
  decomiso_kilos_total: null as number | null,
  inspector1: "García",
  inspector2: "López",
  inspector3: null as string | null,
  inspectores: ["García", "López"],
};

describe("Completar trabajo — habilitación en submit", () => {
  it("SÍ en UI → payload valor_si_no true con id real del catálogo", () => {
    const estados = { 6: "SI" as const };
    expect(validateTieneHabilitacionObligatoria(estados, catalogEnvA)).toBeNull();
    expect(checklistWriteFromEstados(estados, catalogEnvA)).toEqual([
      { item_id: 6, valor_si_no: true },
    ]);
  });

  it("NO en UI → payload valor_si_no false", () => {
    const estados = { 12: "NO" as const };
    expect(validateTieneHabilitacionObligatoria(estados, catalogEnvB)).toBeNull();
    expect(itemsActaInspeccionWriteFromEstados(estados, catalogEnvB)).toEqual([
      { item_id: 12, valor_si_no: false },
    ]);
  });

  it("sin selección → error inline y aviso superior específico (solo habilitación)", () => {
    const result = mergeCompletarTrabajoSubmitValidation(
      formBase,
      actuacionCompletarTrabajoValidationContext(true, false, false),
      {
        uiPolicy: null,
        visitaRealizada: true,
        actaInspeccion: "12345",
        solicitaCarnetManipulador: "",
        telefonoSolicitudCarnet: "",
        faltasNotificacionSubsanadas: "",
      },
      {
        requireTieneHabilitacion: true,
        checklistEstados: { 6: "NONE" },
        checklistCatalog: catalogEnvA,
      }
    );
    expect(result.canSubmit).toBe(false);
    expect(result.fieldErrors.items_acta_inspeccion).toBe(MSG_TIENE_HABILITACION_REQUERIDA);
    expect(result.globalError).toBe(MSG_TIENE_HABILITACION_REQUERIDA);
    expect(result.globalError).not.toBe(MENSAJE_VALIDACION_LOCAL);
  });

  it("con SÍ seleccionado no genera error de habilitación en merge", () => {
    const result = mergeCompletarTrabajoSubmitValidation(
      formBase,
      actuacionCompletarTrabajoValidationContext(true, false, false),
      {
        uiPolicy: null,
        visitaRealizada: true,
        actaInspeccion: "12345",
        solicitaCarnetManipulador: "",
        telefonoSolicitudCarnet: "",
        faltasNotificacionSubsanadas: "",
      },
      {
        requireTieneHabilitacion: true,
        checklistEstados: { 6: "SI" },
        checklistCatalog: catalogEnvA,
      }
    );
    expect(result.fieldErrors.items_acta_inspeccion).toBeUndefined();
  });

  it("planChecklistHydration: catálogo tardío no pisa selección ya tocada", () => {
    expect(
      planChecklistHydration({
        open: true,
        actId: 9,
        hydratedActId: 9,
        touched: true,
        catalogLength: 5,
      })
    ).toBe("skip");
  });
});
