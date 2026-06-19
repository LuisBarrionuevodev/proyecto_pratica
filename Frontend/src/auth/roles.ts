export type AppRole = "admin" | "usuario" | "relevador";

export const ROLE_LABELS: Record<AppRole, string> = {
  admin: "Administrador",
  usuario: "Usuario",
  relevador: "Relevador",
};

/** Rutas permitidas para RELEVADOR (nav + acceso directo). */
export const RELEVADOR_ALLOWED_PATHS: readonly string[] = [
  "/inicio",
  "/cargarActuacion",
  "/cargarRelevamiento",
  "/relevamientos",
  "/perfil",
];

/** Cards de Inicio visibles para RELEVADOR (incluye Mi perfil). */
export const RELEVADOR_INICIO_PATHS: readonly string[] = [
  "/cargarActuacion",
  "/cargarRelevamiento",
  "/relevamientos",
  "/perfil",
];

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
    return role === "admin";
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
