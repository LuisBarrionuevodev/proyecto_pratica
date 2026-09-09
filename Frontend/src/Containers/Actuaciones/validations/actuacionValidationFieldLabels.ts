/**
 * Catálogo único de labels humanos para validación de actuaciones.
 * Usar en toasts, mensajes globales y resúmenes de error (no duplicar en pantallas).
 */
export const ACTUACION_VALIDATION_FIELD_LABELS: Record<string, string> = {
  acta_inspeccion_num: "N.º de acta de inspección",
  acta_comprobacion_num: "N.º de acta de comprobación",
  acta_notificacion_num: "N.º de acta de notificación",
  acta_clausura_num: "N.º de acta de clausura",
  acta_decomiso_num: "N.º de acta de decomiso",
  comprobacion_motivo: "Motivo de comprobación",
  notificacion_motivo_1: "Motivo de notificación",
  notificacion_motivo_2: "Motivo de notificación (2)",
  notificacion_motivo_3: "Motivo de notificación (3)",
  inspectores: "Inspectores",
  calle: "Calle",
  rubro_nombre: "Rubro",
  realizo_nueva_inspeccion: "¿Realizó una nueva inspección?",
  verificar_estado_operativo: "¿Realizó inspección? (Verificar e informar)",
  resultado_cumplimiento_oficio: "Resultado de cumplimiento",
  contraproducencia: "Contraproducencia",
  tipo_actuacion: "Tipo de actuación",
  doc_nro: "N.º de documento",
  contrib_apellido: "Apellido",
  contrib_nombre: "Nombre",
  razon_social: "Razón social",
  numero: "Número o referencia",
  decomiso_kilos_total: "Kilos decomisados",
  // Campos adicionales usados en CRUD / grid
  orden_trabajo_numero: "OT",
  fecha_actuacion: "Fecha de la visita",
  inspector1: "Inspector 1",
  inspector2: "Inspector 2",
  inspector3: "Inspector 3",
  numero_tipo: "Tipo de numeración",
  nombre_local: "Nombre de fantasía",
  notificacion_previa_num: "Acta notificación previa",
  comprobacion_previa_num: "Acta comprobación previa",
  expediente_numero: "Expediente",
  expediente_anio: "Año expediente",
  oficio_numero: "Número de oficio",
  oficio_anio: "Año de oficio",
  oficio_causa: "Causa de oficio",
  numero_oficio: "Número de oficio",
  observaciones_ejecucion: "Observaciones",
};

/**
 * Devuelve el label humano de un campo de actuación.
 *
 * @param field Clave interna del formulario o alias API.
 * @returns Label legible; si no hay entrada en catálogo, devuelve la clave.
 */
export function getActuacionValidationFieldLabel(field: string): string {
  return ACTUACION_VALIDATION_FIELD_LABELS[field] ?? field;
}
