import { lazy, type ComponentType } from "react";

/**
 * Módulos de ruta diferidos (PERF.4). Mis trabajos y Completar trabajo permanecen eager en App.tsx.
 */
function lazyDefault<T extends ComponentType<unknown>>(
  factory: () => Promise<{ default: T }>
) {
  return lazy(factory);
}

export const LazyMapa = lazyDefault(() => import("../Containers/Mapa"));
export const LazyDashboard = lazyDefault(() => import("../Containers/Dashboard"));
export const LazyCargarActuaciones = lazyDefault(() => import("../Containers/CargarActuaciones"));
export const LazyCargarRelevamientos = lazyDefault(() => import("../Containers/CargarRelevamientos"));
export const LazyRelevamientos = lazyDefault(() => import("../Containers/Relevamientos"));
export const LazyGestionDeUsuarios = lazyDefault(() => import("../Containers/GestionDeUsuarios"));
export const LazyRutasTrabajo = lazyDefault(() => import("../Containers/RutasTrabajo"));
export const LazyPendientes = lazyDefault(() => import("../Containers/Actuaciones/Containers/Pendientes"));
export const LazyPendientesVinculacionActa = lazyDefault(
  () => import("../Containers/Actuaciones/Containers/PendientesVinculacionActa")
);
export const LazyPendientesVinculacionOficio = lazyDefault(
  () => import("../Containers/Actuaciones/Containers/PendientesVinculacionOficio")
);
export const LazyGestionNotificacionPage = lazyDefault(
  () => import("../Containers/GestionNotificacion/GestionNotificacionPage")
);
export const LazyActasComprobacionPage = lazyDefault(
  () => import("../Containers/ActasComprobacion/ActasComprobacionPage")
);
export const LazyPerfil = lazyDefault(() => import("../Containers/Perfil"));
export const LazyGestionCapacitacionesPage = lazyDefault(
  () => import("../Containers/Capacitaciones/GestionCapacitacionesPage")
);
export const LazyGestionSistemaPage = lazyDefault(() => import("../Containers/GestionSistema/GestionSistemaPage"));
export const LazyEstablecimientosLayout = lazyDefault(
  () => import("../Containers/Establecimientos/EstablecimientosLayout")
);
export const LazyEstablecimientosListPage = lazyDefault(
  () => import("../Containers/Establecimientos/EstablecimientosListPage")
);
export const LazyHistorialContribuyentePage = lazyDefault(
  () => import("../Containers/Establecimientos/HistorialContribuyentePage")
);
export const LazyEstablecimientoDetallePage = lazyDefault(
  () => import("../Containers/Establecimientos/EstablecimientoDetallePage")
);
