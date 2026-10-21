/**
 * Body explícito para `PUT /actuaciones/:id` (canal Cargar actuación / Gestión).
 *
 * Nunca hace spread del detalle de lectura: solo claves del contrato backend.
 */

/** Paridad con `ActuacionGridRowIn` (PUT Admin/Usuario). Sin expediente/oficio ni metadata GET. */
export const ACTUACION_ADMIN_PUT_ALLOWED_KEYS: readonly string[] = [
  "id",
  "carga_solo_comprobacion",
  "orden_trabajo_numero",
  "fecha_actuacion",
  "rubro_nombre",
  "nombre_local",
  "tipo_actuacion",
  "contraproducencia",
  "limpiar_contraproducencia",
  "limpiar_contribuyente",
  "actas_a_quitar",
  "inspectores",
  "inspector1",
  "inspector2",
  "inspector3",
  "calle",
  "numero",
  "numero_tipo",
  "doc_nro",
  "contrib_apellido",
  "contrib_nombre",
  "razon_social",
  "acta_inspeccion_num",
  "items_acta_inspeccion",
  "cantidad_personas_sin_carnet_sanidad",
  "acta_notificacion_num",
  "notificacion_motivo_1",
  "notificacion_motivo_2",
  "notificacion_motivo_3",
  "acta_comprobacion_num",
  "comprobacion_motivo",
  "acta_clausura_num",
  "acta_decomiso_num",
  "decomiso_kilos_total",
  "solicita_carnet_manipulador",
  "telefono_contacto_solicitud_carnet",
  "faltas_notificacion_subsanadas",
  "observaciones_ejecucion",
  "realizo_nueva_inspeccion",
] as const;

/** Paridad con `ActuacionInspectorPatchIn` (extra=forbid en backend). */
export const ACTUACION_INSPECTOR_PUT_ALLOWED_KEYS: readonly string[] = [
  "rubro_nombre",
  "nombre_local",
  "tipo_actuacion",
  "contraproducencia",
  "limpiar_contraproducencia",
  "limpiar_contribuyente",
  "actas_a_quitar",
  "calle",
  "numero",
  "numero_tipo",
  "doc_nro",
  "contrib_apellido",
  "contrib_nombre",
  "razon_social",
  "acta_inspeccion_num",
  "items_acta_inspeccion",
  "cantidad_personas_sin_carnet_sanidad",
  "acta_notificacion_num",
  "notificacion_motivo_1",
  "notificacion_motivo_2",
  "notificacion_motivo_3",
  "acta_comprobacion_num",
  "comprobacion_motivo",
  "acta_clausura_num",
  "acta_decomiso_num",
  "decomiso_kilos_total",
  "notificacion_previa_num",
  "comprobacion_previa_num",
  "solicita_carnet_manipulador",
  "telefono_contacto_solicitud_carnet",
  "faltas_notificacion_subsanadas",
  "observaciones_ejecucion",
] as const;

/** Metadata de lectura que nunca debe salir en el PUT (defensa en tests). */
export const ACTUACION_PUT_READ_ONLY_METADATA_KEYS: readonly string[] = [
  "actuacion_editable",
  "actuacion_bloqueada_por_expediente",
  "motivo_bloqueo_edicion",
  "calle_cargada",
  "calle_raw",
  "esquina_cargada",
  "esquina_key",
  "can_edit_rubro",
  "rubro_edit_blocked_reason",
  "can_edit_domicilio",
  "domicilio_edit_blocked_reason",
  "ui_policy",
  "seguimiento",
  "domicilio",
  "rubro",
  "contribuyente",
  "media_resumen",
  "documentacion_contexto",
  "origen_reinspeccion_oficio",
  "origen_reinspeccion_notificacion",
  "expediente_numero",
  "expediente_anio",
  "oficio_numero",
  "oficio_anio",
  "oficio_causa",
] as const;

export type BuildActuacionUpdatePayloadOptions = {
  inspectorSelfService?: boolean;
};

function shouldIncludePutValue(key: string, value: unknown): boolean {
  if (value === undefined) return false;
  if (key === "limpiar_contraproducencia" || key === "limpiar_contribuyente") {
    return value === true;
  }
  return true;
}

/**
 * Arma el JSON del PUT copiando solo claves permitidas (sin spread del row de lectura).
 */
export function pickActuacionPutFields(
  source: Record<string, unknown>,
  allowedKeys: readonly string[]
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of allowedKeys) {
    if (!Object.prototype.hasOwnProperty.call(source, key)) continue;
    const value = source[key];
    if (!shouldIncludePutValue(key, value)) continue;
    out[key] = value;
  }
  return out;
}

/**
 * Payload final de `PUT /actuaciones/:id` según rol (grid completo vs patch Inspector).
 */
export function buildActuacionUpdatePayload(
  preparedRow: Record<string, unknown>,
  options?: BuildActuacionUpdatePayloadOptions
): Record<string, unknown> {
  const allowed = options?.inspectorSelfService
    ? ACTUACION_INSPECTOR_PUT_ALLOWED_KEYS
    : ACTUACION_ADMIN_PUT_ALLOWED_KEYS;
  return pickActuacionPutFields(preparedRow, allowed);
}
