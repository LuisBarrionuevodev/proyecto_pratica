import {
  esFlujoVerificarInformar,
  esReinspeccionOficioGenerico,
  esVerificarInformarOficio,
} from "./completarTrabajoTipoIniciadorUi";
import type { ShowContribDomicilioEditableOpts } from "./completarTrabajoReinspeccionNotificacionUi";

export type IdentityOperativaMode = "COMPLETE_HISTORICAL" | "COMPLETE_EXISTING";

export type IdentityModeUiOpts = ShowContribDomicilioEditableOpts & {
  identityMode?: IdentityOperativaMode | string | null;
};

/** Bloque de identidad (titular / documento / rubro) en Verificar e informar con nueva inspección. */
export function showIdentityVerificarInformarEnCompletarTrabajo(
  tipoIniciador: string | null | undefined,
  opts?: IdentityModeUiOpts
): boolean {
  if (!opts?.identityMode) return false;
  if (opts.realizoNuevaInspeccion !== "si") return false;
  if (esVerificarInformarOficio(tipoIniciador)) return true;
  return (
    esReinspeccionOficioGenerico(tipoIniciador) &&
    esFlujoVerificarInformar(tipoIniciador, opts.tipoActuacionOficio)
  );
}

/** Campos de identidad editables solo en modo histórico incompleto. */
export function identityFieldsEditableEnCompletarTrabajo(
  identityMode?: IdentityOperativaMode | string | null
): boolean {
  return identityMode === "COMPLETE_HISTORICAL";
}
