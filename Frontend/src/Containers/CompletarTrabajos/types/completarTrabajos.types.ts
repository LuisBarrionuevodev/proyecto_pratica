/**
 * Tipos del módulo Completar trabajos.
 * Filas alineadas a trabajo precargado desde ruta publicada (origen futuro: API).
 */

export type CompletarTrabajosEmptyProps = {
  /** Fecha inicial del selector (YYYY-MM-DD). Si se omite, usa la fecha local del día. */
  initialFecha?: string;
  /** Al confirmar fecha en el empty state, navega a la vista de grilla. */
  onVerTrabajos?: (fecha: string) => void;
};

/** Fila de la grilla de completar trabajos del día (mock / futuro backend). */
export interface TrabajoDelDiaRow {
  id: number | string;

  // BASE (precargado)
  fecha: string;
  tipoIniciador: string;
  ordenTrabajo: string | null;
  inspectores: string;
  calle: string;
  interseccion: string;

  // IDENTIFICACIÓN
  nombre: string;
  apellido: string;
  dni: string;

  // RESULTADO
  contraproducencia: string | null;
  actaInspeccion: string | null;
  notificacion: string | null;
  actaComprobacion: string | null;
  motivo: string | null;
  actaClausura: string | null;
  actaDecomiso: string | null;
  kilosDecomisados: number | null;

  // MOTIVOS DETALLADOS
  motivo1: string | null;
  motivo2: string | null;
  motivo3: string | null;
}
