import { describe, expect, it } from "vitest";

import {
  identityFieldsEditableEnCompletarTrabajo,
  showIdentityVerificarInformarEnCompletarTrabajo,
} from "./completarTrabajoIdentityModeUi";
import { showContribuyenteDomicilioEditableEnCompletarTrabajo } from "./completarTrabajoReinspeccionNotificacionUi";

describe("completarTrabajoIdentityModeUi", () => {
  it("COMPLETE_HISTORICAL habilita edición de identidad", () => {
    expect(identityFieldsEditableEnCompletarTrabajo("COMPLETE_HISTORICAL")).toBe(true);
    expect(identityFieldsEditableEnCompletarTrabajo("COMPLETE_EXISTING")).toBe(false);
  });

  it("muestra bloque de identidad en verificar+nueva inspección", () => {
    expect(
      showIdentityVerificarInformarEnCompletarTrabajo("VERIFICAR_INFORMAR_OFICIO", {
        realizoNuevaInspeccion: "si",
        identityMode: "COMPLETE_HISTORICAL",
      })
    ).toBe(true);
    expect(
      showIdentityVerificarInformarEnCompletarTrabajo("REINSPECCION_OFICIO", {
        tipoActuacionOficio: "VERIFICAR E INFORMAR",
        realizoNuevaInspeccion: "si",
        identityMode: "COMPLETE_EXISTING",
      })
    ).toBe(true);
    expect(
      showIdentityVerificarInformarEnCompletarTrabajo("VERIFICAR_INFORMAR_OFICIO", {
        realizoNuevaInspeccion: "no",
        identityMode: "COMPLETE_HISTORICAL",
      })
    ).toBe(false);
  });

  it("COMPLETE_EXISTING oculta bloque editable de contrib/domicilio", () => {
    expect(
      showContribuyenteDomicilioEditableEnCompletarTrabajo("VERIFICAR_INFORMAR_OFICIO", {
        identityMode: "COMPLETE_EXISTING",
        realizoNuevaInspeccion: "si",
      })
    ).toBe(false);
    expect(
      showContribuyenteDomicilioEditableEnCompletarTrabajo("VERIFICAR_INFORMAR_OFICIO", {
        identityMode: "COMPLETE_HISTORICAL",
        realizoNuevaInspeccion: "si",
      })
    ).toBe(true);
  });
});
