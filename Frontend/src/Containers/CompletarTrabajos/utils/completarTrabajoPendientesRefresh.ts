type RefreshListener = () => void;

const listeners = new Set<RefreshListener>();

/** Aviso en segundo plano: resumen/calendario y listas deben re-sincronizar con el backend. */
export function notifyCompletarTrabajoPendientesRefresh(): void {
  for (const listener of listeners) {
    try {
      listener();
    } catch {
      // no bloquear otros listeners
    }
  }
}

export function subscribeCompletarTrabajoPendientesRefresh(listener: RefreshListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
