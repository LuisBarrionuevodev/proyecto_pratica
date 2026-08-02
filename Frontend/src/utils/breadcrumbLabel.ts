import { matchPath } from "react-router-dom";
import { routeLabels } from "../constants/menuItems";

/**
 * Resuelve el texto del breadcrumb del AppLayout para rutas estáticas y dinámicas.
 */
export function resolveBreadcrumbLabel(pathname: string): string {
  if (matchPath({ path: "/establecimientos/:id", end: true }, pathname)) {
    return "Establecimientos › Detalle";
  }
  if (matchPath({ path: "/establecimientos/historial-contribuyente", end: true }, pathname)) {
    return "Establecimientos › Historial por DNI/CUIT";
  }
  return routeLabels[pathname] ?? "Vista";
}
