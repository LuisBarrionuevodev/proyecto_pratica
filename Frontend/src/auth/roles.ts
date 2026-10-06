export type AppRole = "admin" | "usuario" | "relevador" | "relevamiento";

export const ROLE_LABELS: Record<AppRole, string> = {
  admin: "Administrador",
  usuario: "Usuario",
  relevador: "Inspector",
  relevamiento: "Relevamiento",
};

export const COMPLETAR_TRABAJOS_PATH = "/completarTrabajos";
export const ACTUACIONES_PATH = "/actuaciones";
export const DASHBOARD_PATH = "/dashboard";
export const MAPA_PATH = "/mapa";
export const CARGAR_RELEVAMIENTO_PATH = "/cargarRelevamiento";
export const GESTION_RELEVAMIENTOS_PATH = "/relevamientos";

/** Rutas permitidas para Inspector (`relevador`). */
export const RELEVADOR_ALLOWED_PATHS: readonly string[] = [
  "/inicio",
  ACTUACIONES_PATH,
  COMPLETAR_TRABAJOS_PATH,
  DASHBOARD_PATH,
  MAPA_PATH,
  "/perfil",
];

/** Rutas permitidas para perfil Relevamiento (carga/gestión). */
export const RELEVAMIENTO_ALLOWED_PATHS: readonly string[] = [
  "/inicio",
  CARGAR_RELEVAMIENTO_PATH,
  GESTION_RELEVAMIENTOS_PATH,
  "/perfil",
];

/** Cards de Inicio visibles para Inspector (`relevador`). */
export const RELEVADOR_INICIO_PATHS: readonly string[] = [
  ACTUACIONES_PATH,
  COMPLETAR_TRABAJOS_PATH,
  DASHBOARD_PATH,
  MAPA_PATH,
  "/perfil",
];

/** Cards de Inicio visibles para perfil Relevamiento. */
export const RELEVAMIENTO_INICIO_PATHS: readonly string[] = [
  CARGAR_RELEVAMIENTO_PATH,
  GESTION_RELEVAMIENTOS_PATH,
  "/perfil",
];

export function completarTrabajosLabelForRole(role: AppRole): string {
  return role === "relevador" ? "Completar mis trabajos" : "Completar trabajo";
}

export function actuacionesLabelForRole(role: AppRole): string {
  return role === "relevador" ? "Mis trabajos" : "Actuaciones";
}

export function indicadoresLabelForRole(role: AppRole): string {
  return role === "relevador" ? "Mis indicadores" : "Indicadores";
}

export function mapaLabelForRole(role: AppRole): string {
  return role === "relevador" ? "Mi mapa" : "Mapa";
}

export function cargarRelevamientoLabelForRole(role: AppRole): string {
  return role === "relevamiento" ? "Cargar relevamientos" : "Cargar relevamientos y denuncias";
}

export function gestionRelevamientosLabelForRole(role: AppRole): string {
  return role === "relevamiento" ? "Gestión de relevamientos" : "Relevamientos y denuncias";
}

export function resolveMenuLabelForRole(role: AppRole, path: string, defaultText: string): string {
  if (path === COMPLETAR_TRABAJOS_PATH) {
    return completarTrabajosLabelForRole(role);
  }
  if (path === ACTUACIONES_PATH) {
    return actuacionesLabelForRole(role);
  }
  if (path === DASHBOARD_PATH) {
    return indicadoresLabelForRole(role);
  }
  if (path === MAPA_PATH) {
    return mapaLabelForRole(role);
  }
  if (path === CARGAR_RELEVAMIENTO_PATH) {
    return cargarRelevamientoLabelForRole(role);
  }
  if (path === GESTION_RELEVAMIENTOS_PATH) {
    return gestionRelevamientosLabelForRole(role);
  }
  return defaultText;
}

/**
 * Ruta de destino tras login según perfil.
 */
export function postLoginPathForRole(role: AppRole): string {
  if (role === "relevamiento") {
    return CARGAR_RELEVAMIENTO_PATH;
  }
  return "/inicio";
}

/**
 * Indica si un rol puede navegar a la ruta (path exacto o prefijo de detalle).
 */
export function isPathAllowedForRole(role: AppRole, path: string): boolean {
  const p = path.split("?")[0].replace(/\/$/, "") || "/";

  if (role === "admin") {
    return true;
  }

  if (role === "usuario") {
    return p !== "/gestionDeUsuarios";
  }

  if (role === "relevador") {
    return RELEVADOR_ALLOWED_PATHS.some((allowed) => p === allowed);
  }

  if (role === "relevamiento") {
    return RELEVAMIENTO_ALLOWED_PATHS.some((allowed) => p === allowed);
  }

  return false;
}

/**
 * Filtra ítems de menú/cards según rol.
 */
export function isMenuPathVisibleForRole(role: AppRole, path: string): boolean {
  if (role === "admin") {
    return true;
  }
  if (path === "/gestionDeUsuarios") {
    return false;
  }
  if (role === "relevador") {
    return RELEVADOR_ALLOWED_PATHS.includes(path);
  }
  if (role === "relevamiento") {
    return RELEVAMIENTO_ALLOWED_PATHS.includes(path);
  }
  return true;
}

export function normalizeAppRole(raw: string | null | undefined): AppRole {
  if (raw === "admin" || raw === "relevador" || raw === "relevamiento") return raw;
  return "usuario";
}
