/**
 * Payload PUT para Inspector → Mis trabajos → Editar datos.
 *
 * Debe mantenerse alineado con
 * `Backend/app/domains/actuaciones/services/actuacion_inspector_put_policy.py`
 * (`_INSPECTOR_FORBIDDEN_PAYLOAD_KEYS`). El backend sigue siendo la defensa final.
 *
 * El identificador de la actuación va solo en la URL (`PUT /actuaciones/:id`), no en el body.
 */
export const INSPECTOR_SELF_SERVICE_PUT_FORBIDDEN_KEYS: readonly string[] = [
  "id",
  "orden_trabajo",
  "orden_trabajo_numero",
  "orden_trabajo_id",
  "fecha_actuacion",
  "inspectores",
  "inspector1",
  "inspector2",
  "inspector3",
  "domicilio_id",
  "created_by_user_id",
  "created_at",
  "updated_at",
  "ruta_item_id",
  "iniciador_ruta_id",
  "ruta_trabajo_id",
  "actuacion_id",
] as const;

export type InspectorSelfServicePutForbiddenKey =
  (typeof INSPECTOR_SELF_SERVICE_PUT_FORBIDDEN_KEYS)[number];

/**
 * Elimina del body las claves de pertenencia/asignación/ruta que el Inspector no puede enviar.
 */
export function buildInspectorSelfServiceUpdateBody<T extends Record<string, unknown>>(
  body: T
): T {
  const out: Record<string, unknown> = { ...body };
  for (const key of INSPECTOR_SELF_SERVICE_PUT_FORBIDDEN_KEYS) {
    delete out[key];
  }
  return out as T;
}
