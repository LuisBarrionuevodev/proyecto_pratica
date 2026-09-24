/**
 * Tipos UI — Gestión de capacitaciones (mock hasta backend).
 */

export interface ParticipanteCapacitacion {
  id: string;
  nombre: string;
  apellido: string;
  dni: string;
  telefono: string;
  mail: string;
  lugarTrabajo: string;
  examenAprobado: boolean;
  nota: string | null;
}

export interface CapacitacionRow {
  id: string;
  nombre: string;
  sede: string;
  fechaInicio: string;
  /** Nombres de promotores; la cantidad es `promotores.length`. */
  promotores: string[];
  participantes: ParticipanteCapacitacion[];
}

export type CapacitacionFormValues = {
  nombre: string;
  fechaInicio: string;
  sede: string;
  cantPromotores: string;
};
