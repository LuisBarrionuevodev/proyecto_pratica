import type { ICompletarTrabajoDetalleResponse } from "../../../api/completarTrabajoApi";
import { getCompletarTrabajoDetalle } from "../../../api/completarTrabajoApi";
import { getRutaItemArchivos } from "../../../api/mediaApi";
import type { RutaItemArchivosListResponse } from "../../../features/media/mediaTypes";
import {
  detalleConfirmaCompletarTrabajoSinEvidenciasPendientes,
  type FetchDetalleConfirmaSinEvidenciasResult,
} from "./completarTrabajoEvidenciasConfirm";

const DEFAULT_MAX_ATTEMPTS = 3;
const DEFAULT_DELAY_MS = 280;

export function sleepMs(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export type WaitCompletarTrabajoEvidenciasSyncOptions = {
  fetchDetalle?: (rutaItemId: number) => Promise<ICompletarTrabajoDetalleResponse>;
  fetchArchivos?: (rutaItemId: number) => Promise<RutaItemArchivosListResponse>;
  maxAttempts?: number;
  delayMs?: number;
  sleep?: (ms: number) => Promise<void>;
};

/**
 * Reconsulta detalle (y opcionalmente archivos) hasta que el backend refleje cero pendientes
 * o se agoten los intentos. No usa estado React previo.
 */
export async function waitForCompletarTrabajoEvidenciasBackendSync(
  rutaItemId: number,
  options?: WaitCompletarTrabajoEvidenciasSyncOptions
): Promise<FetchDetalleConfirmaSinEvidenciasResult> {
  const fetchDetalle = options?.fetchDetalle ?? getCompletarTrabajoDetalle;
  const fetchArchivos = options?.fetchArchivos ?? getRutaItemArchivos;
  const maxAttempts = options?.maxAttempts ?? DEFAULT_MAX_ATTEMPTS;
  const delayMs = options?.delayMs ?? DEFAULT_DELAY_MS;
  const sleep = options?.sleep ?? sleepMs;

  let last: FetchDetalleConfirmaSinEvidenciasResult = { status: "pendiente" };

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      if (attempt > 0) {
        try {
          await fetchArchivos(rutaItemId);
        } catch {
          /* archivos auxiliar; la decisión es por detalle */
        }
      }

      const det = await fetchDetalle(rutaItemId);
      if (detalleConfirmaCompletarTrabajoSinEvidenciasPendientes(det)) {
        return { status: "completo" };
      }
      last = { status: "pendiente" };
    } catch {
      last = { status: "error" };
      return last;
    }

    if (attempt < maxAttempts - 1) {
      await sleep(delayMs);
    }
  }

  return last;
}
