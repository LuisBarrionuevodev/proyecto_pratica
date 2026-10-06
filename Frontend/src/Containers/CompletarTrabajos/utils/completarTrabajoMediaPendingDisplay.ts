import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";

export type MediaResumenCategoria = {
  ready: number;
  pending: number;
  max: number;
  pendientes: number;
};

export type MediaResumenRow = {
  foto_acta?: MediaResumenCategoria;
  foto_documentacion_local?: MediaResumenCategoria;
  foto_inspeccion?: MediaResumenCategoria;
  tiene_evidencias_pendientes?: boolean;
  evidencias_pendientes_total?: number;
};

export function mediaResumenFromRow(row: ICompletarTrabajoPendienteRow): MediaResumenRow | null {
  const raw = (row as { media_resumen?: MediaResumenRow }).media_resumen;
  return raw ?? null;
}

export function rowTieneEvidenciasPendientes(row: ICompletarTrabajoPendienteRow): boolean {
  if ((row as { trabajo_guardado_evidencias_pendientes?: boolean }).trabajo_guardado_evidencias_pendientes) {
    return true;
  }
  const resumen = mediaResumenFromRow(row);
  return Boolean(resumen?.tiene_evidencias_pendientes);
}

export function lineasEvidenciasPendientes(resumen: MediaResumenRow | null): string[] {
  if (!resumen) return [];
  const lines: string[] = [];
  const actas = resumen.foto_acta;
  const docs = resumen.foto_documentacion_local;
  const insp = resumen.foto_inspeccion;
  if (actas && actas.pending > 0) {
    lines.push(`Actas: ${actas.pending} pendientes de ${actas.max}`);
  }
  if (docs && docs.pending > 0) {
    lines.push(`Documentación: ${docs.pending} pendientes de ${docs.max}`);
  }
  if (insp && insp.pending > 0) {
    lines.push(`Inspección: ${insp.pending} pendientes de ${insp.max}`);
  }
  return lines;
}
