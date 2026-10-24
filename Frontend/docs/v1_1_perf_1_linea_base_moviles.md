# V1.1-PERF.1 — Línea base de rendimiento móvil (Digitaliza)

**Fecha:** 2026-10-24  
**Alcance:** medición y relevamiento **sin cambios de comportamiento** en frontend, backend ni media.  
**Rama / estado:** análisis sobre `Frontend/` actual (build reproducido en esta fecha).

---

## 1. Entorno de medición

| Dimensión | Valor documentado |
|-----------|-------------------|
| **Dispositivo físico (TTI / UX)** | *Pendiente QA:* Android gama media (≥4 GB RAM), pantalla ~360×800. Registrar modelo exacto al medir. |
| **Navegador móvil** | Chrome Android (misma versión que usen inspectores en campo) o Safari iOS si aplica. |
| **Emulación (desarrollo)** | Chrome DevTools → Device Toolbar → *Mid-tier mobile* + **CPU: 4× slowdown**, **Network: Fast 3G** o *Slow 4G* según red de campo. |
| **Build analizado** | `npm run build` en `Frontend/` — exit 0, ~18.7 s (2026-10-24). |
| **API** | Misma base que producción/staging usada en QA (`VITE_API_BASE_URL`). Las fórmulas de requests abajo son independientes del host. |

### Criterio “pantalla usable” (TTI operativo)

Para cada escenario, marcar **T0** al iniciar la acción (tap en menú / fila / botón) y **T1** cuando se cumple **todo**:

1. Desaparece el spinner principal del flujo (o el skeleton equivalente).
2. La lista o el formulario acepta scroll y tap sin overlay bloqueante.
3. En galerías: los tiles muestran miniatura o estado de error por tile (no solo skeleton infinito).

Registrar **TTI = T1 − T0** (mediana de 3 corridas). Adjuntar captura de **Network** (filtro `Fetch/XHR`) y, si es posible, export **HAR**.

---

## 2. Línea base de bundle (carga inicial SPA)

| Asset | Tamaño (min) | gzip |
|-------|--------------|------|
| `index-*.js` (chunk principal) | **5 773 kB** | **1 852 kB** |
| `article-cell-editor-*.js` (Glide cells) | 724 kB | 231 kB |
| `index-*.css` | 69 kB | 25 kB |
| `DashboardProductividadSection-*.js` | 6.6 kB | 1.6 kB |

**Observación:** casi todas las rutas privadas se importan de forma **eager** en `App.tsx` (Actuaciones, Completar trabajos, Mapa, Dashboard, Cargar actuaciones con Glide, etc.). El único `React.lazy` relevante encontrado es `DashboardProductividadSectionLazy.tsx`. El primer paint post-login paga el chunk principal completo aunque el inspector solo use “Mis trabajos”.

---

## 3. Relevamiento de código (sin modificar)

### 3.1 Rutas y pantallas (import inmediato)

- `Frontend/src/App.tsx`: imports estáticos de todos los módulos de negocio; sin code-splitting por ruta.
- Inspector (`relevador`): menú acotado en `roles.ts` — `/actuaciones` (**Mis trabajos**), `/completarTrabajos`, `/dashboard`, `/mapa`, `/perfil`.

### 3.2 Galerías y fotos

| Flujo | Listado servidor | Miniaturas |
|-------|------------------|------------|
| **ActuacionMediaGallery** (editar actuación, Cargar más fotos) | `GET /ruta-items/{id}/archivos` al montar (`refreshGalleryFromServer`) | Por cada imagen READY: `GET /archivos/{id}/download-url` en `MediaThumbnailTile` + `GET` a URL firmada (Storage) |
| **Completar trabajo modal** | `useRutaItemReadyArchivos` → mismo `getRutaItemArchivos` al abrir modal | Misma lógica vía `MediaUploadSection` → `MediaThumbnailTile` |
| **Preview** | — | `MediaPreviewDialog` vuelve a pedir `download-url` al abrir |

No hay caché en memoria de `download-url` ni de blobs de imagen entre montajes. **Reabrir la misma galería** repite listado + N URLs.

`MediaThumbnailTile` usa `loading="lazy"` en `<img>`, pero el **efecto** dispara `getMediaDownloadUrl` en mount de cada tile (no hay virtualización de lista).

### 3.3 Catálogos

| Cache | Mecanismo | Endpoints típicos (1ª vez en sesión) |
|-------|-----------|--------------------------------------|
| `fetchCompletarTrabajoCatalogsCached` | `memoryCache` + `inflight` | motivos, motivos comprobación, contraproducencias, inspectores, rubros, ítems acta inspección (6 en paralelo) |
| `fetchRubrosCatalogoCached` | idem | rubros (compartido con Mapa y otros) |

**Prefetch:** al montar `CompletarTrabajos/index.tsx` se llama `fetchCompletarTrabajoCatalogsCached()` aunque el usuario no abra el modal. La grilla también usa `useCompletarTrabajoCatalogs()` (misma cache; no duplica si ya inflight/resuelto).

### 3.4 Componentes pesados en el bundle principal

- **Glide Data Grid** + `article-cell-editor` chunk: Cargar actuaciones (no ruta inspector típica, pero sí en el JS inicial).
- **Leaflet / mapa:** `MapPage` + `MapaCanvas` (tiles mapa + capas operativas).
- **Dashboard:** múltiples hooks de indicadores + MUI charts; sección productividad lazy.
- **PDF / documentos:** `@react-pdf` y builders en rutas administrativas (incluidos en grafo de imports).

### 3.5 Requests “de fondo” (inspector)

- `useInspectorFotosPendientesCount` (banner en layout): `getInspectorFotosPendientesCount` al montar + **cada 60 s** + tras eventos de subida (`mediaUploadSessionNotify`).
- **Mis trabajos** (`ActuacionesContainer`): al montar, **siempre** `getActuacionesPendientesSummary` (pestaña pendientes admin). Para rol `relevador` el backend responde **403** (`test_inspector_mis_actuaciones_v1_1_4.py`); el frontend hace `.catch(() => undefined)` — request fallida silenciosa en cada visita a `/actuaciones`.

---

## 4. Tabla de escenarios y métricas

**Leyenda columnas TTI:** rellenar en QA físico/emulado.  
**Requests / download-url:** modelo **verificado en código** (2026-10-24); validar contra HAR en QA.

Variables: **F** = fotos imagen READY visibles en galería del escenario (suma de categorías mostradas). **C** = catálogos Completar trabajo ya en cache de sesión (0 = fría, 1 = caliente).

| # | Escenario | TTI usable (QA) | Requests XHR/fetch (modelo) | `download-url` (modelo) | Imágenes Storage (modelo) | Transferencia (orden de magnitud) | Duplicados / ruido | HTTP errors |
|---|-----------|-----------------|----------------------------|-------------------------|---------------------------|-----------------------------------|--------------------|-------------|
| 1 | Login → **Mis trabajos** (`/actuaciones`, rol inspector) | *medir* | Auth + `GET /actuaciones?…` (lista) + banner fotos pendientes + **1×** `GET /actuaciones/pendientes/summary` | 0 | 0 | Chunk JS ~1.9 MB gzip + JSON lista | Summary 403 inspector; poll banner 60 s | **403** `/actuaciones/pendientes/summary` esperado |
| 2 | Abrir **Completar mis trabajos** → modal, **0 fotos** | *medir* | Si visitó `/completarTrabajos` antes: **C=1** (0 catálogos extra). Siempre: `getCompletarTrabajoDetalle` + `getRutaItemArchivos` | 0 | 0 | Detalle JSON pequeño | Catálogos 6× solo 1ª vez en sesión | — |
| 3 | Mismo modal, **5 fotos** READY | *medir* | Detalle + archivos + **5×** `download-url` | **5** | **5** | JSON + **~5× tamaño foto** (URLs full size, sin thumbs API) | Misma lista archivos 1×; URLs sin cache | — |
| 4 | Mismo modal, **10+ fotos** READY | *medir* | Detalle + archivos + **F×** `download-url` | **F (≥10)** | **F** | Crece **lineal con F**; riesgo saturación red móvil | Idem | — |
| 5 | **Cargar más fotos** (dialog inspector, galería con evidencias) | *medir* | `getRutaItemArchivos` + **F×** `download-url` + Storage | **F** | **F** | Similar a filas 3–4 | Montaje nuevo = refetch completo | — |
| 6 | **Editar actuación** con galería embebida | *medir* | PUT no incluido; al abrir diálogo: catálogos edición (varios GET grid) + `getRutaItemArchivos` + **F×** `download-url` | **F** | **F** | Modal grande + media | Catálogos CRUD async (`catalogsLoading`) | — |
| 7 | **Reabrir** misma galería (cerrar y volver a abrir) | *medir* | Repite fila 5 o 6 **íntegro** (sin cache URLs) | **F** (de nuevo) | **F** (de nuevo) | **~2×** coste media vs una sola apertura | Duplicación por diseño actual | — |
| 8 | Abrir **Mi mapa** (`/mapa`) | *medir* | Distritos + inspectores + rubros (cache) + hooks `useMapaOperativo` (GeoJSON/listas según modo) + tiles OSM | 0* | tiles mapa | JS ya pagado; pico JSON + tiles | Rubros/inspectores cacheados en sesión | — |
| 9 | Abrir **Mis indicadores** (`/dashboard`) | *medir* | Varios `GET` indicadores (ejecutivo, riesgo, no realizadas, filtros) + lazy productividad al tab | 0 | 0 | JSON agregados + charts | Productividad: 1 chunk extra ~6.6 kB | — |

\*Mapa: las imágenes son tiles del proveedor de mapas, no `download-url` de archivos.

### Fórmulas rápidas (galería / completar)

```
XHR_media ≈ 1 (archivos list) + F (download-url) + 1 (detalle modal, solo Completar)
GET_imagen ≈ F (una por miniatura; preview suma +1 por apertura)
```

---

## 5. Evidencia de requests (patrones observables en Network)

Filtrar por `download-url`, `archivos`, `ruta-items`, `completar`, `actuaciones`, `indicadores`.

**Ejemplo A — Inspector entra a Mis trabajos**

```
GET /actuaciones?desde=…&hasta=…&page=1&page_size=50     200
GET /actuaciones/pendientes/summary?desde=…&hasta=…       403  ← rol relevador (ruido)
GET …/inspector/fotos-pendientes/count (o equivalente)   200
```

**Ejemplo B — Abrir Completar trabajo con F=8 fotos en una categoría**

```
GET /completar-trabajo/.../detalle                         200
GET /ruta-items/{id}/archivos                              200
GET /archivos/{id1}/download-url                           200
… (×8)
GET https://…storage…/…                                    200 (×8, paralelo)
```

**Ejemplo C — Reabrir galería Mis trabajos**

Repetición de **Ejemplo B** sin reutilizar respuestas de `download-url` (nuevo mount `MediaThumbnailTile`).

**Build (evidencia local 2026-10-24):** Vite reporta chunk principal `index-*.js` **5 773 kB** (gzip **1 852 kB**) y warning `> 500 kB`.

---

## 6. Observaciones UX móvil (checklist QA)

Marcar en dispositivo real durante las mismas corridas de TTI:

- [ ] Pantalla blanca >2 s tras login o tras tap en menú
- [ ] Tirones al abrir modal Completar trabajo con muchas fotos
- [ ] Scroll del diálogo trabado mientras cargan miniaturas
- [ ] Galería: muchos skeletons simultáneos (tormenta de requests)
- [ ] Mapa: lentitud al cambiar modo / rango de fechas
- [ ] Dashboard: cambio de tab con overlay de refresh prolongado

---

## 7. Top 5 cuellos de botella (impacto × riesgo de cambio)

| Rank | Cuello | Impacto en móvil | Evidencia | Riesgo si se toca sin diseño |
|------|--------|------------------|-----------|------------------------------|
| **1** | **N× `download-url` + descarga full image por miniatura** al abrir galería/modal | Muy alto con F≥5; red y CPU | `MediaThumbnailTile.tsx`, `MediaUploadSection`, `ActuacionMediaGallery` | Medio — debe preservar permisos y flujo 2E.x |
| **2** | **Bundle único ~5.7 MB** (sin split por ruta inspector) | Alto en primer acceso / cache fría | `App.tsx`, build Vite | Bajo si solo lazy de rutas no usadas por inspector |
| **3** | **`getRutaItemArchivos` en cada montaje** de galería sin ETag/cache cliente | Medio; duplica en reabrir | `ActuacionMediaGallery`, `useRutaItemReadyArchivos` | Bajo |
| **4** | **403 recurrente** `GET /actuaciones/pendientes/summary` en Mis trabajos | Bajo–medio (ruido, batería, logs) | `ActuacionesContainer.tsx` L118–122; test backend 403 | Muy bajo (guard por rol) |
| **5** | **Prefetch catálogos Completar** al entrar al módulo + banner poll 60 s | Medio en sesiones largas | `CompletarTrabajos/index.tsx`, `useInspectorFotosPendientesCount` | Bajo |

**Hipótesis prioritaria para PERF.2:** carga diferida de miniaturas (viewport / límite de concurrencia) + cache de `download-url` hasta `expires_at`, **sin** cambiar Storage ni pipeline de subida.

---

## 8. Propuesta de tickets PERF.2+

| Ticket | Objetivo | Fuera de alcance |
|--------|----------|------------------|
| **PERF.2** | Virtualizar o limitar concurrencia de `getMediaDownloadUrl` + mostrar thumbs progresivos; cache URL por `archivo_id` hasta expiración | Comprimir originales, cambiar bucket, cola upload |
| **PERF.3** | No llamar `getActuacionesPendientesSummary` si `role === relevador` | Lógica pendientes admin |
| **PERF.4** | `React.lazy` rutas no inspector (Glide, actas comprobación, gestión usuarios, etc.) | Refactor de routers / suspense UX |
| **PERF.5** | Diferir prefetch catálogos Completar hasta abrir modal o grilla del día | Invalidación de cache catálogos |
| **PERF.6** | Mapa: medir y diferir capas / reducir refetch en cambio de filtro | Backend geoespacial |
| **PERF.7** | Dashboard inspector: cargar solo tabs visitados; consolidar indicadores | Contratos API |

Cada ticket debe repetir escenarios de §4 y comparar contra esta línea base.

---

## 9. Qué permanece intacto (media y estabilidad)

No modificar en PERF.2 sin ticket explícito de media:

- Cola de subida, reintentos, reconciliación post-red (**V1.1-MEDIA.2E.x**).
- `crear_upload_intent`, idempotencia SHA, delete/re-upload.
- Compresión de originales en cliente, políticas de Storage Railway.
- Backend, cron, migraciones.

---

## 10. Cierre PERF.1

- [x] Relevamiento de código y modelo de requests documentado.
- [x] Línea base de bundle registrada.
- [ ] TTI y HAR por escenario en dispositivo objetivo (completar filas *medir* en §4 y archivar HAR en carpeta QA del equipo).

Con la evidencia de código, el primer cambio **seguro y acotado** recomendado es **PERF.2** (miniaturas bajo demanda + cache de URL), validando con F=10+ en Fast 3G antes de tocar el bundle.

---

## Commit sugerido

```text
V1.1-PERF.1: documenta línea base de rendimiento móvil.
```
