# V1.1-PERF.4 — Code splitting por ruta

**Fecha:** 2026-10-25  
**Build:** `npm run build` en `Frontend/`

## Comparativa chunk principal

| Métrica | Antes (PERF.1) | Después (PERF.4) | Δ |
|---------|----------------|------------------|---|
| `index-*.js` (min) | **5 773 kB** | **4 473 kB** | **−1 300 kB (~22 %)** |
| gzip | **1 852 kB** | **1 463 kB** | **−389 kB (~21 %)** |

## Rutas eager (bootstrap inspector)

- Login, recuperar cuenta, inicio, acerca-de
- `AppLayout`, sesión, guards
- **`/actuaciones`** (Mis trabajos)
- **`/completarTrabajos`**

## Rutas lazy (`src/routing/lazyRouteModules.tsx`)

Mapa, Dashboard, Cargar actuación (Glide), relevamientos, gestión admin, pendientes, establecimientos, perfil, etc.

## Chunks diferidos relevantes (build 2026-10-25)

| Asset (aprox.) | Tamaño min | gzip | Notas |
|----------------|------------|------|--------|
| `article-cell-editor-*.js` | 724 kB | 231 kB | Glide (ya no en entry) |
| `index-DI3K5UKr.js` | 417 kB | 141 kB | Leaflet / mapa |
| `index-CVQQ81Kk.js` | 315 kB | 94 kB | Dashboard / indicadores |
| `index-DtZ4ZcC-.js` | 185 kB | 56 kB | Rutas trabajo u otro módulo grande |
| `ActasComprobacionPage-*.js` | 100 kB | 26 kB | Gestión actas |
| `GestionNotificacionPage-*.js` | 57 kB | 17 kB | |

Al entrar solo a **Mis trabajos**, Network no debe solicitar los chunks de Mapa/Dashboard hasta navegar a esas rutas (verificar filtro JS en DevTools).

## UX carga

- `AppLayout` envuelve `<Outlet />` en `<Suspense fallback={<RouteModuleFallback />}>`.
- Texto: **«Cargando módulo…»** + `CircularProgress`.

## Verificación

```powershell
cd Frontend
npm test -- --run src/routing/appPerf4.test.ts src/utils/authBootstrap.test.ts src/Containers/Mapa/MapPage.pr6c12.test.tsx
npm run build
```

## Fuera de alcance (intacto)

- Media, galerías PERF.2, bootstrap PERF.3, permisos backend.
