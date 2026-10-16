import {
  getCompletarTrabajoDetalle,
  type ICompletarTrabajoDetalleResponse,
} from "../../../api/completarTrabajoApi";
import {
  isCompletarTrabajoOperativoFinalizado,
  isCompletarTrabajoSoloFotosMode,
} from "./completarTrabajoSoloFotosMode";

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
  const guardadoConFotos =
    isCompletarTrabajoSoloFotosMode(det.ui_policy, det.row) ||
    isCompletarTrabajoOperativoFinalizado(det.row);

  const resumen = det.row.media_resumen;
  const totalPend = resumen?.evidencias_pendientes_total ?? 0;
  const pendientes =
    totalPend > 0 ||
    (resumen?.tiene_evidencias_pendientes === true && totalPend > 0) ||
    (det.row.trabajo_guardado_evidencias_pendientes === true && totalPend > 0);

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
