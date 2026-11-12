/**
 * Actas de origen de la actuación ancla (`IniciadorRuta.actuacion_id`).
 * Nunca corresponden a decomiso/kilos/clausura de la visita de reinspección.
 */
export interface IOrigenActas {
  actuacion_origen_id: number | null;
  acta_decomiso_num: string | null;
  decomiso_kilos_total: number | null;
  acta_clausura_num: string | null;
}
