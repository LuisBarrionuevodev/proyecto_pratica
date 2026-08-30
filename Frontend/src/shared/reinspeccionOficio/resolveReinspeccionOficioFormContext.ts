import type { IActuacionListItem } from "../../api/actuacionesListApi";
import {
  esFlujoCumplimientoRatificacion,
  esFlujoVerificarInformar,
  esRatificacionOficio,
  esReinspeccionOficioGenerico,
  esTipoActuacionVerificarInformar,
  tipoActuacionFijoDesdeIniciadorOficio,
} from "../../Containers/CompletarTrabajos/utils/completarTrabajoTipoIniciadorUi";
import {
  isRatificacionClausura,
  isRatificacionDecomiso,
  isReinspeccionPorNotificacion,
  isVerificarEInformar,
} from "../../Containers/Actuaciones/utils/actuacionesExportPdfResumen";
import {
  resolveVerificarEstadoFromPersisted,
  type VerificarEstadoResuelto,
} from "./verificarEstadoOperativo";

export type ReinspeccionOficioFormMode = "completar" | "edit";

export type ReinspeccionOficioCumplimientoUi =
  | ""
  | "CUMPLE"
  | "NO_CUMPLE"
  | "CONTRAPRODUCENCIA";

export type ReinspeccionOficioFormContext = {
  esCircuitoOficio: boolean;
  subtipo: string;
  subtipoReadonly: boolean;
  esRatificacion: boolean;
  esVerificar: boolean;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  contraproducencia: string;
  realizoNuevaInspeccion: "" | "si" | "no";
  /** Estado operativo canónico Verificar (incluye INCONSISTENTE si persistido híbrido). */
  verificarEstadoOperativo: VerificarEstadoResuelto;
  resultadoPersistido: string | null;
  realizoPersistido: boolean | null;
};

function normTipo(t: string | null | undefined): string {
  return (t ?? "").trim().toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ");
}

function esCircuitoOficioRow(row: {
  tipo_actuacion?: string | null;
  documentacion_contexto?: { circuito?: string | null } | null;
}): boolean {
  if (row.documentacion_contexto?.circuito === "REINSPECCION_OFICIO") return true;
  if (isRatificacionClausura(row as IActuacionListItem)) return true;
  if (isRatificacionDecomiso(row as IActuacionListItem)) return true;
  if (isVerificarEInformar(row as IActuacionListItem)) return true;
  return false;
}

/**
 * Reconstruye cumplimiento efectivo desde datos persistidos (incluye histórico contra sin resultado).
 */
export function resolveCumplimientoUiFromPersisted(row: {
  resultado_cumplimiento_oficio?: string | null;
  contraproducencia?: string | null;
}): ReinspeccionOficioCumplimientoUi {
  const res = (row.resultado_cumplimiento_oficio ?? "").trim().toUpperCase();
  const contra = (row.contraproducencia ?? "").trim();
  if (res === "CUMPLE") return "CUMPLE";
  if (contra) return "CONTRAPRODUCENCIA";
  if (res === "NO_CUMPLE") return "NO_CUMPLE";
  return "";
}

export function realizoNuevaInspeccionFromPersisted(
  val: boolean | null | undefined
): "" | "si" | "no" {
  if (val === true) return "si";
  if (val === false) return "no";
  return "";
}

export type ResolveReinspeccionOficioFormContextInput = {
  row: IActuacionListItem;
  mode: ReinspeccionOficioFormMode;
  tipoIniciador?: string | null;
  tipoActuacionOficio?: string | null;
};

/**
 * Contexto compartido Completar Trabajo / Editar Actuación para circuito oficio.
 */
export function resolveReinspeccionOficioFormContext(
  input: ResolveReinspeccionOficioFormContextInput
): ReinspeccionOficioFormContext | null {
  const { row, mode, tipoIniciador, tipoActuacionOficio } = input;
  if (isReinspeccionPorNotificacion(row)) return null;

  const esCircuito = esCircuitoOficioRow(row);
  if (!esCircuito && mode === "edit") return null;

  const tIni = tipoIniciador ?? null;
  const subtipoFijo = tipoActuacionFijoDesdeIniciadorOficio(tIni);
  const subtipo =
    subtipoFijo ||
    (tipoActuacionOficio ?? "").trim() ||
    (row.tipo_actuacion ?? "").trim();

  const esRatificacion =
    isRatificacionClausura(row) ||
    isRatificacionDecomiso(row) ||
    esFlujoCumplimientoRatificacion(tIni, subtipo) ||
    normTipo(subtipo).includes("RATIFICACION");

  const esVerificar =
    isVerificarEInformar(row) ||
    esFlujoVerificarInformar(tIni, subtipo) ||
    esTipoActuacionVerificarInformar(subtipo);

  if (mode === "completar") {
    if (!esReinspeccionOficioGenerico(tIni) && !esRatificacionOficio(tIni) && !esFlujoVerificarInformar(tIni)) {
      if (!esRatificacion && !esVerificar) return null;
    }
  } else if (!esCircuito) {
    return null;
  }

  if (!esRatificacion && !esVerificar && mode === "edit" && !esCircuito) {
    return null;
  }

  return {
    esCircuitoOficio: esCircuito || Boolean(tIni && esReinspeccionOficioGenerico(tIni)),
    subtipo,
    subtipoReadonly: false,
    esRatificacion,
    esVerificar,
    cumplimientoUi: resolveCumplimientoUiFromPersisted(row),
    contraproducencia: (row.contraproducencia ?? "").trim(),
    realizoNuevaInspeccion: realizoNuevaInspeccionFromPersisted(row.realizo_nueva_inspeccion),
    verificarEstadoOperativo: resolveVerificarEstadoFromPersisted(row),
    resultadoPersistido: row.resultado_cumplimiento_oficio ?? null,
    realizoPersistido: row.realizo_nueva_inspeccion ?? null,
  };
}

/** Infiere tipo_iniciador promovido desde subtipo persistido (edición Actuaciones). */
export function tipoIniciadorInferidoDesdeActuacion(row: IActuacionListItem): string {
  if (isRatificacionClausura(row)) return "RATIFICACION_CLAUSURA_OFICIO";
  if (isRatificacionDecomiso(row)) return "RATIFICACION_DECOMISO_OFICIO";
  if (isVerificarEInformar(row)) return "VERIFICAR_INFORMAR_OFICIO";
  return "REINSPECCION_OFICIO";
}

export function cumplimientoUiToPayload(cumplimientoUi: ReinspeccionOficioCumplimientoUi): {
  resultado_cumplimiento_oficio: string | null;
  contraproducencia: string | null;
} {
  if (cumplimientoUi === "CUMPLE") {
    return { resultado_cumplimiento_oficio: "CUMPLE", contraproducencia: null };
  }
  if (cumplimientoUi === "NO_CUMPLE") {
    return { resultado_cumplimiento_oficio: "NO_CUMPLE", contraproducencia: null };
  }
  if (cumplimientoUi === "CONTRAPRODUCENCIA") {
    return { resultado_cumplimiento_oficio: null, contraproducencia: null };
  }
  return { resultado_cumplimiento_oficio: null, contraproducencia: null };
}
