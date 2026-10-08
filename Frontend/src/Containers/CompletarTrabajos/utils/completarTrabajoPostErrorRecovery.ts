import {
  getCompletarTrabajoDetalle,
  type ICompletarTrabajoDetalleResponse,
} from "../../../api/completarTrabajoApi";

export type CompletarTrabajoRecoveryStatus =
  | "completo"
  | "guardado_fotos_pendientes"
  | "no_guardado"
  | "desconocido";

/**
 * Clasifica el estado real del rutaItem tras un error de red (MEDIA.2D).
 */
export function classifyCompletarTrabajoDetalle(
  det: ICompletarTrabajoDetalleResponse
): CompletarTrabajoRecoveryStatus {
  const soloFotos = det.ui_policy?.solo_evidencias_pendientes === true;
  const guardadoConFotos =
    soloFotos ||
    det.row.trabajo_guardado_evidencias_pendientes === true ||
    det.ui_policy?.cierre_alfanumerico_readonly === true;

  const resumen = det.row.media_resumen;
  const pendientes =
    resumen?.tiene_evidencias_pendientes === true ||
    (resumen?.evidencias_pendientes_total ?? 0) > 0;

  if (guardadoConFotos) {
    return pendientes ? "guardado_fotos_pendientes" : "completo";
  }
  return "no_guardado";
}

/**
 * Reconsulta GET detalle y devuelve el estado operativo real.
 */
export async function fetchCompletarTrabajoRecoveryStatus(
  rutaItemId: number
): Promise<CompletarTrabajoRecoveryStatus> {
  try {
    const det = await getCompletarTrabajoDetalle(rutaItemId);
    return classifyCompletarTrabajoDetalle(det);
  } catch {
    return "desconocido";
  }
}

export type CompletarTrabajoRecoveryApplyHandlers = {
  onCompleto: () => void;
  onGuardadoFotosPendientes: (det: ICompletarTrabajoDetalleResponse) => void;
  onNoGuardado: () => void;
};

/**
 * Aplica UI según estado reconsultado (sin error rojo si el trabajo ya quedó guardado).
 */
export async function tryRecoverCompletarTrabajoTrasErrorRed(
  rutaItemId: number,
  handlers: CompletarTrabajoRecoveryApplyHandlers
): Promise<boolean> {
  try {
    const det = await getCompletarTrabajoDetalle(rutaItemId);
    const status = classifyCompletarTrabajoDetalle(det);
    if (status === "completo") {
      handlers.onCompleto();
      return true;
    }
    if (status === "guardado_fotos_pendientes") {
      handlers.onGuardadoFotosPendientes(det);
      return true;
    }
    if (status === "no_guardado") {
      handlers.onNoGuardado();
      return false;
    }
    return false;
  } catch {
    return false;
  }
}
