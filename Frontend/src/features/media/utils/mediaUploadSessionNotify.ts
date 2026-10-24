import { notifyCompletarTrabajoPendientesRefresh } from "../../../Containers/CompletarTrabajos/utils/completarTrabajoPendientesRefresh";

type Listener = () => void;

const inspectorPendientesListeners = new Set<Listener>();

/** Tras carga/reconciliación: refrescar banner de fotos pendientes del Inspector. */
export function subscribeInspectorFotosPendientesRefresh(listener: Listener): () => void {
  inspectorPendientesListeners.add(listener);
  return () => inspectorPendientesListeners.delete(listener);
}

export function notifyInspectorFotosPendientesRefresh(): void {
  for (const listener of inspectorPendientesListeners) {
    try {
      listener();
    } catch {
      /* ignore */
    }
  }
}

/** Invalida listados Completar trabajo y conteo de pendientes del Inspector. */
export function notifyMediaUploadSessionSettled(): void {
  notifyCompletarTrabajoPendientesRefresh();
  notifyInspectorFotosPendientesRefresh();
}
