import { clearCompletarTrabajoCatalogsCache } from "../Containers/CompletarTrabajos/hooks/completarTrabajoCatalogsCache";
import { clearGridCatalogSessionCaches } from "../utils/gridCatalogSessionCache";
import { clearInspectoresCatalogCache } from "../utils/inspectoresCatalogCache";
import { clearRubrosCatalogCache } from "../utils/rubrosCatalogCache";
import { clearProfileMeSessionCache } from "./profileMeSession";

/**
 * Resetea caches de sesión SPA (perfil y catálogos). No usa localStorage.
 */
export function clearBootstrapSessionCaches(): void {
  clearProfileMeSessionCache();
  clearGridCatalogSessionCaches();
  clearInspectoresCatalogCache();
  clearRubrosCatalogCache();
  clearCompletarTrabajoCatalogsCache();
}
