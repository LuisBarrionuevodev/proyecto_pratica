import { useEffect } from "react";
import { LAST_RUTA_STORAGE_KEY } from "../types";

/**
 * Lee el id de ruta persistido en sessionStorage.
 *
 * @returns id numérico válido o null si no hay valor usable
 */
export function readPersistedRutaId(): number | null {
  const saved = window.sessionStorage.getItem(LAST_RUTA_STORAGE_KEY);
  if (!saved) return null;
  const rutaIdSaved = Number(saved);
  if (!Number.isFinite(rutaIdSaved) || rutaIdSaved <= 0) return null;
  return rutaIdSaved;
}

/**
 * Persiste el id de ruta activo en sessionStorage.
 */
export function persistRutaId(id: number): void {
  window.sessionStorage.setItem(LAST_RUTA_STORAGE_KEY, String(id));
}

/**
 * Elimina la ruta persistida de sessionStorage.
 */
export function clearPersistedRutaId(): void {
  window.sessionStorage.removeItem(LAST_RUTA_STORAGE_KEY);
}

/**
 * Hidrata el detalle de la ruta al montar el contenedor, si hay id guardado.
 *
 * @param loadRutaDetail - callback estable (p. ej. useCallback) que carga el detalle por id
 */
export function useRutasTrabajoSession(loadRutaDetail: (id: number) => Promise<void>): void {
  useEffect(() => {
    const rutaIdSaved = readPersistedRutaId();
    if (rutaIdSaved == null) return;
    void loadRutaDetail(rutaIdSaved);
  }, [loadRutaDetail]);
}
