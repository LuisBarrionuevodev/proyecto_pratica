import type { ICompletarTrabajoUiPolicy } from "../../../api/completarTrabajoApi";

export type SolicitaCarnetUiValue = "" | "si" | "no";
export type FaltasSubsanadasUiValue = "" | "si" | "no";

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
