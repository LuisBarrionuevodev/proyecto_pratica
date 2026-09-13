import type { ICompletarTrabajoPendienteDiaResumen } from "../../../api/completarTrabajoApi";

/**
 * Etiqueta de pendientes para celda del calendario (singular/plural).
 * Retorna `undefined` si no debe mostrarse contador (0 o ausente).
 */
export function formatPendientesDiaLabel(total: number): string | undefined {
  if (total <= 0) return undefined;
  return total === 1 ? "1 pendiente" : `${total} pendientes`;
}

/**
 * Contador de pendientes para un día del resumen (misma fuente que el carrusel legacy).
 */
export function pendientesFooterLabel(
  row: ICompletarTrabajoPendienteDiaResumen | undefined
): string | undefined {
  if (!row) return undefined;
  return formatPendientesDiaLabel(row.total);
}
