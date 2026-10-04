export type AppRole = "admin" | "usuario" | "relevador";

export const ROLE_LABELS: Record<AppRole, string> = {
  admin: "Administrador",
  usuario: "Usuario",
  relevador: "Inspector",
};

export const COMPLETAR_TRABAJOS_PATH = "/completarTrabajos";
export const ACTUACIONES_PATH = "/actuaciones";

/** Rutas permitidas para RELEVADOR (nav + acceso directo). */
export const RELEVADOR_ALLOWED_PATHS: readonly string[] = [
  "/inicio",
  ACTUACIONES_PATH,
  COMPLETAR_TRABAJOS_PATH,
  "/perfil",
];

/** Cards de Inicio visibles para RELEVADOR (incluye Mi perfil). */
export const RELEVADOR_INICIO_PATHS: readonly string[] = [
  ACTUACIONES_PATH,
  COMPLETAR_TRABAJOS_PATH,
  "/perfil",
];

export function completarTrabajosLabelForRole(role: AppRole): string {
  return role === "relevador" ? "Completar mis trabajos" : "Completar trabajo";
}

export function actuacionesLabelForRole(role: AppRole): string {
  return role === "relevador" ? "Mis actuaciones" : "Actuaciones";
}

export function resolveMenuLabelForRole(role: AppRole, path: string, defaultText: string): string {
  if (path === COMPLETAR_TRABAJOS_PATH) {
    return completarTrabajosLabelForRole(role);
  }
  if (path === ACTUACIONES_PATH) {
    return actuacionesLabelForRole(role);
  }
  return defaultText;
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
  return true;
}

export function normalizeAppRole(raw: string | null | undefined): AppRole {
  if (raw === "admin" || raw === "relevador") return raw;
  return "usuario";
}
