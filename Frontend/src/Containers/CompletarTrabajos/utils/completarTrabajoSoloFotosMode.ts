import type {
  ICompletarTrabajoPendienteRow,
  ICompletarTrabajoUiPolicy,
} from "../../../api/completarTrabajoApi";

export type CompletarTrabajoSoloFotosRowSlice = Pick<
  ICompletarTrabajoPendienteRow,
  | "estado_operativo"
  | "iniciador_estado"
  | "trabajo_guardado_evidencias_pendientes"
  | "media_resumen"
>;

/**
 * Estado operativo FINALIZADO del ruta_item (cierre alfanumérico ya persistido).
 */
export function isCompletarTrabajoOperativoFinalizado(
  row: CompletarTrabajoSoloFotosRowSlice | null | undefined
): boolean {
  if (!row) return false;
  const estado = (row.estado_operativo ?? row.iniciador_estado ?? "").toUpperCase();
  return estado === "FINALIZADO";
}

/**
 * Modo UI “solo fotos”: no validar ni reenviar POST /cerrar; únicamente pipeline de media.
 */
export function isCompletarTrabajoSoloFotosMode(
  uiPolicy: ICompletarTrabajoUiPolicy | null | undefined,
  row: CompletarTrabajoSoloFotosRowSlice | null | undefined
): boolean {
  if (uiPolicy?.solo_evidencias_pendientes === true) return true;
  if (uiPolicy?.cierre_alfanumerico_readonly === true) return true;
  if (!row) return false;
  if (row.trabajo_guardado_evidencias_pendientes === true) return true;

  if (!isCompletarTrabajoOperativoFinalizado(row)) return false;

  const totalPend = row.media_resumen?.evidencias_pendientes_total ?? 0;
  if (totalPend > 0) return true;
  if (row.media_resumen?.tiene_evidencias_pendientes === true) return true;

  return false;
}
