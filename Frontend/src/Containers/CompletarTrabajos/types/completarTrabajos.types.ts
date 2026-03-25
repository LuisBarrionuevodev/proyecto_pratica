/**
 * Tipos del módulo Completar trabajos.
 * Filas de grilla: ver `ICompletarTrabajoPendienteRow` en `api/completarTrabajoApi.ts`.
 */

export type CompletarTrabajosEmptyProps = {
  /** Fecha inicial del selector (YYYY-MM-DD). Si se omite, usa la fecha local del día. */
  initialFecha?: string;
  /** Al confirmar fecha en el empty state, navega a la vista de grilla. */
  onVerTrabajos?: (fecha: string) => void;
};
