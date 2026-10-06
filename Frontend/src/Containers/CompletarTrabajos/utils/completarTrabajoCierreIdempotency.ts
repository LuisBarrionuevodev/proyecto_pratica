/** UUID estable por sesión de cierre de un RutaItem (reintentos de red). */

export function newCompletarTrabajoCierreIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
