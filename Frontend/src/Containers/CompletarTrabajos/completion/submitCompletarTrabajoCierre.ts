import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { postCompletarTrabajoCerrar } from "../../../api/completarTrabajoApi";
import { buildCompletarTrabajoCierreBodyFromInline } from "../utils/buildCompletarTrabajoCierreBody";

export type SubmitCompletarTrabajoCierreOptions = {
  includeTipoActuacion?: boolean;
  omitPrecargadoPr2?: boolean;
  /** Sustituye inspectores del grupo; solo enviar si el usuario los editó en el modal. */
  inspectoresExplicitos?: string[];
};

/**
 * Ejecuta el POST de cierre (mismo contrato que la edición inline).
 */
export async function submitCompletarTrabajoCierreFromRow(
  row: ICompletarTrabajoPendienteRow,
  values: Record<string, unknown>,
  options?: SubmitCompletarTrabajoCierreOptions
): Promise<void> {
  const body = buildCompletarTrabajoCierreBodyFromInline(row, values, {
    includeTipoActuacion: options?.includeTipoActuacion === true,
    omitPrecargadoPr2: options?.omitPrecargadoPr2 === true,
    ...(options?.inspectoresExplicitos !== undefined
      ? { inspectoresExplicitos: options.inspectoresExplicitos }
      : {}),
  });
  await postCompletarTrabajoCerrar(row.ruta_item_id, body);
}
