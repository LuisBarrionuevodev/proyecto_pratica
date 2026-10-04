import { matchPath } from "react-router-dom";
import { routeLabels } from "../constants/menuItems";
import {
  actuacionesLabelForRole,
  completarTrabajosLabelForRole,
  indicadoresLabelForRole,
  type AppRole,
} from "../auth/roles";

/**
 * Resuelve el texto del breadcrumb del AppLayout para rutas estáticas y dinámicas.
 */
export function resolveBreadcrumbLabel(pathname: string, role?: AppRole | null): string {
  if (matchPath({ path: "/establecimientos/:id", end: true }, pathname)) {
    return "Establecimientos › Detalle";
  }
  if (matchPath({ path: "/establecimientos/historial-contribuyente", end: true }, pathname)) {
    return "Establecimientos › Historial por DNI/CUIT";
  }
  if (pathname === "/completarTrabajos" && role === "relevador") {
    return completarTrabajosLabelForRole("relevador");
  }
  if (pathname === "/actuaciones" && role === "relevador") {
    return actuacionesLabelForRole("relevador");
  }
  if (pathname === "/dashboard" && role === "relevador") {
    return indicadoresLabelForRole("relevador");
  }
  return routeLabels[pathname] ?? "Vista";
}
