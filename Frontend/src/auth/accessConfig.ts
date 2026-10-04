import { menuSections, type MenuSection } from "../constants/menuItems";
import { INICIO_ACCESOS, type InicioAccesoItem } from "../Containers/Inicio/inicioAccesosData";
import {
  actuacionesLabelForRole,
  completarTrabajosLabelForRole,
  indicadoresLabelForRole,
  mapaLabelForRole,
  isMenuPathVisibleForRole,
  resolveMenuLabelForRole,
  type AppRole,
} from "./roles";

/**
 * Fuente única de permisos de módulos (nav + cards de Inicio).
 */
export function canAccessModule(role: AppRole, modulePath: string): boolean {
  return isMenuPathVisibleForRole(role, modulePath);
}

export function getVisibleHomeCards(role: AppRole): InicioAccesoItem[] {
  return INICIO_ACCESOS.filter((item) => canAccessModule(role, item.to)).map((item) => {
    if (item.to === "/completarTrabajos") {
      return { ...item, title: completarTrabajosLabelForRole(role) };
    }
    if (item.to === "/actuaciones") {
      return { ...item, title: actuacionesLabelForRole(role) };
    }
    if (item.to === "/dashboard") {
      return { ...item, title: indicadoresLabelForRole(role) };
    }
    if (item.to === "/mapa") {
      return { ...item, title: mapaLabelForRole(role) };
    }
    return item;
  });
}

export function getVisibleMenuSections(role: AppRole): MenuSection[] {
  return menuSections
    .map((section) => ({
      ...section,
      items: section.items
        .filter((item) => canAccessModule(role, item.path))
        .map((item) => ({
          ...item,
          text: resolveMenuLabelForRole(role, item.path, item.text),
        })),
    }))
    .filter((section) => section.items.length > 0);
}
