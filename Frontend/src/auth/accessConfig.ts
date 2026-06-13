import { menuSections, type MenuSection } from "../constants/menuItems";
import { INICIO_ACCESOS, type InicioAccesoItem } from "../Containers/Inicio/inicioAccesosData";
import { isMenuPathVisibleForRole, type AppRole } from "./roles";

/**
 * Fuente única de permisos de módulos (nav + cards de Inicio).
 */
export function canAccessModule(role: AppRole, modulePath: string): boolean {
  return isMenuPathVisibleForRole(role, modulePath);
}

export function getVisibleHomeCards(role: AppRole): InicioAccesoItem[] {
  return INICIO_ACCESOS.filter((item) => canAccessModule(role, item.to));
}

export function getVisibleMenuSections(role: AppRole): MenuSection[] {
  return menuSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => canAccessModule(role, item.path)),
    }))
    .filter((section) => section.items.length > 0);
}
