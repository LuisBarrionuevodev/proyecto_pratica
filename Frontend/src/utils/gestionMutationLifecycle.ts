/**
 * Ciclo de vida de mutaciones en Gestión (Notificación / Comprobación).
 * Separa persistencia crítica (POST/PATCH/DELETE) de reconciliación posterior (refetch bandejas).
 */

export const GESTION_PERSIST_OPS = {
  notifAltaExpediente: "notif-alta-expediente",
  compExpedienteSalida: "comp-expediente-salida",
  compOficioAlta: "comp-oficio-alta",
} as const;

export type GestionPersistOp = (typeof GESTION_PERSIST_OPS)[keyof typeof GESTION_PERSIST_OPS];

export type GestionPersistKey = {
  actuacionId: number;
  op: GestionPersistOp;
};

/** Mensaje cuando la persistencia OK pero falla el refresh en background. */
export const GESTION_RECONCILE_REFRESH_MSG =
  "Los datos se guardaron correctamente, pero no se pudo actualizar el listado. Usá Actualizar para reintentar.";

/**
 * Indica si la fila/modal actual está en persistencia crítica para la operación dada.
 */
export function isPersistingForRow(
  persistKey: GestionPersistKey | null,
  actuacionId: number | null | undefined,
  op: GestionPersistOp
): boolean {
  if (persistKey == null || actuacionId == null) return false;
  return persistKey.actuacionId === actuacionId && persistKey.op === op;
}

/** Avanza el token de mutación y devuelve el valor asignado. */
export function nextMutationSeq(seqRef: { current: number }): number {
  seqRef.current += 1;
  return seqRef.current;
}

/** Comprueba si el token sigue siendo la mutación más reciente. */
export function isMutationSeqCurrent(seqRef: { current: number }, token: number): boolean {
  return seqRef.current === token;
}

/**
 * Invalida callbacks de mutaciones/reconciliaciones anteriores al abrir otro registro.
 */
export function invalidatePendingMutationCallbacks(seqRef: { current: number }): void {
  seqRef.current += 1;
}

/**
 * Limpia la clave de persistencia solo si coincide con actuación y operación esperadas.
 */
export function clearPersistKeyIfMatch(
  current: GestionPersistKey | null,
  actuacionId: number,
  op: GestionPersistOp
): GestionPersistKey | null {
  if (current == null) return null;
  if (current.actuacionId === actuacionId && current.op === op) return null;
  return current;
}

/**
 * Ejecuta reconciliación (refetch) en background sin bloquear el handler principal.
 */
export function runGestionReconcile(task: () => Promise<void>, onError?: (err: unknown) => void): void {
  void (async () => {
    try {
      await task();
    } catch (err) {
      onError?.(err);
    }
  })();
}
