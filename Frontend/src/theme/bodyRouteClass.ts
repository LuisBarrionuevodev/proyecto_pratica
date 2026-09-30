/**
 * Clases en `document.body` para fondos de shell vs rutas públicas (login/recuperar).
 */

const PUBLIC_ROUTE_CLASS = "public-route";
const AUTHENTICATED_ROUTE_CLASS = "authenticated-route";

/** Marca el body como ruta pública (sin fondo de shell autenticado). */
export function setBodyPublicRoute(active: boolean): void {
  document.body.classList.toggle(PUBLIC_ROUTE_CLASS, active);
  if (active) {
    document.body.classList.remove(AUTHENTICATED_ROUTE_CLASS);
  }
}

/** Marca el body como shell autenticado (AppLayout). */
export function setBodyAuthenticatedRoute(active: boolean): void {
  document.body.classList.toggle(AUTHENTICATED_ROUTE_CLASS, active);
  if (active) {
    document.body.classList.remove(PUBLIC_ROUTE_CLASS);
  }
}
