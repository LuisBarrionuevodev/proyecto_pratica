import type { ICompletarTrabajoUiPolicy } from "../../../api/completarTrabajoApi";
import { isValidActaInspeccionNum } from "../../Actuaciones/Components/InspeccionChecklistFields";

export type SolicitaCarnetUiValue = "" | "si" | "no";
export type FaltasSubsanadasUiValue = "" | "si" | "no";

export type CompletarTrabajoSeguimientoValidationInput = {
  uiPolicy: ICompletarTrabajoUiPolicy | null | undefined;
  visitaRealizada: boolean;
  actaInspeccion: string;
  solicitaCarnetManipulador: SolicitaCarnetUiValue;
  telefonoSolicitudCarnet: string;
  faltasNotificacionSubsanadas: FaltasSubsanadasUiValue;
};

/**
 * Validación de seguimiento en Completar trabajo (mismas reglas que el payload de cierre).
 */
export function validateCompletarTrabajoSeguimientoFields(
  input: CompletarTrabajoSeguimientoValidationInput
): Record<string, string> {
  const errors: Record<string, string> = {};
  const carnetVisible =
    input.visitaRealizada && mostrarBloqueSolicitudCarnet(input.uiPolicy);
  const subsVisible =
    input.visitaRealizada && mostrarBloqueSubsanacionNotificacion(input.uiPolicy);
  const actaInspeccionValida = isValidActaInspeccionNum(input.actaInspeccion);

  if (carnetVisible && actaInspeccionValida) {
    if (input.solicitaCarnetManipulador !== "si" && input.solicitaCarnetManipulador !== "no") {
      errors.solicita_carnet_manipulador = "Indique si solicita carnet de manipulador.";
    } else if (input.solicitaCarnetManipulador === "si" && !input.telefonoSolicitudCarnet.trim()) {
      errors.telefono_contacto_solicitud_carnet =
        "Ingrese el teléfono de contacto del solicitante.";
    }
  }

  if (subsVisible && actaInspeccionValida) {
    if (
      input.faltasNotificacionSubsanadas !== "si" &&
      input.faltasNotificacionSubsanadas !== "no"
    ) {
      errors.faltas_notificacion_subsanadas =
        "Indique si se subsanaron las faltas de la notificación.";
    }
  }

  return errors;
}

export function mostrarBloqueSolicitudCarnet(
  uiPolicy: ICompletarTrabajoUiPolicy | null | undefined
): boolean {
  return Boolean(uiPolicy?.mostrar_solicitud_carnet_manipulador);
}

export function mostrarBloqueSubsanacionNotificacion(
  uiPolicy: ICompletarTrabajoUiPolicy | null | undefined
): boolean {
  return Boolean(uiPolicy?.mostrar_subsanacion_notificacion);
}

export function boolToSolicitaCarnetUi(v: boolean | null | undefined): SolicitaCarnetUiValue {
  if (v === true) return "si";
  if (v === false) return "no";
  return "";
}

export function solicitaCarnetUiToBool(v: SolicitaCarnetUiValue): boolean | undefined {
  if (v === "si") return true;
  if (v === "no") return false;
  return undefined;
}

export function boolToFaltasSubsanadasUi(v: boolean | null | undefined): FaltasSubsanadasUiValue {
  if (v === true) return "si";
  if (v === false) return "no";
  return "";
}

export function faltasSubsanadasUiToBool(v: FaltasSubsanadasUiValue): boolean | undefined {
  if (v === "si") return true;
  if (v === "no") return false;
  return undefined;
}
