import {
  TIPO_ACTUACION_REINSPECCION_OFICIO,
  tipoActuacionInicialReinspeccionOficio,
  tipoActuacionReinspeccionOficioOpts,
} from "../../Containers/CompletarTrabajos/utils/completarTrabajoReinspeccionOficioUi";

function normTipo(t: string | null | undefined): string {
  return (t ?? "").trim().toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ");
}

function normSubtipo(subtipo: string | null | undefined): string {
  return (subtipo ?? "").trim().toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

/** Mapping canónico subtipo actuación → tipo_iniciador (paridad backend). */
export function tipoIniciadorDesdeSubtipoActuacionOficio(subtipo: string | null | undefined): string | null {
  const t = normSubtipo(subtipo);
  if (t === "RATIFICACION DE CLAUSURA") return "RATIFICACION_CLAUSURA_OFICIO";
  if (t === "RATIFICACION DE DECOMISO") return "RATIFICACION_DECOMISO_OFICIO";
  if (t === "VERIFICAR E INFORMAR") return "VERIFICAR_INFORMAR_OFICIO";
  return null;
}

export { TIPO_ACTUACION_REINSPECCION_OFICIO, tipoActuacionReinspeccionOficioOpts, tipoActuacionInicialReinspeccionOficio };

export function subtipoOficioEsRatificacion(subtipo: string | null | undefined): boolean {
  return normTipo(subtipo).includes("RATIFICACION");
}

export function subtipoOficioEsVerificar(subtipo: string | null | undefined): boolean {
  return normTipo(subtipo) === normTipo("VERIFICAR E INFORMAR");
}

export function subtipoOficioEsValido(subtipo: string | null | undefined): boolean {
  const t = (subtipo ?? "").trim();
  return (TIPO_ACTUACION_REINSPECCION_OFICIO as readonly string[]).includes(t);
}
