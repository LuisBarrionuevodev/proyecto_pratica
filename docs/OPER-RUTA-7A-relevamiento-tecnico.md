# OPER-RUTA.7A — Relevamiento técnico Ruta Trabajo / Mapa / Candidatos / Urgentes

> **Alcance:** solo relevamiento y mediciones. Sin cambios funcionales de negocio.  
> **Fecha:** 2026-08-19  
> **Confirmación:** no se tocó Asignación final, Mapa final, publicar, Completar Trabajo, PR11/PR12, geocode, indicadores, exports, CRUDs ni reglas pool/ruta cerradas.

---

## Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| **¿Qué tarda más?** | **Backend M4** (`pendientes-contexto`) al seleccionar distrito — ~16 s en BD de test para 1 página. |
| **¿Backend o frontend?** | **Principalmente backend** (load-all + filtro Python + N+1 elegibilidad). Frontend amplifica con **multi-página secuencial** y **re-fetch en cada cambio de pool**. |
| **¿Cuántos registros?** | M4: ~4.196 candidatos SQL → 131 en distrito → 92 agregables (distrito 1, ruta 6764). Urgentes: ~1.869 → 1.556 agregables. |
| **¿Todo de golpe?** | **Sí en backend** (`.all()` antes de paginar). Frontend M4 puede pedir hasta **40 × 500 = 20.000** filas en loop. |
| **¿Urgentes = filtro de candidatos?** | **Sí conceptualmente** (prioridad ≥ 3, no RELEVAMIENTO + agregables 6J). Hoy es **endpoint separado** con la misma query base costosa. |
| **¿Cuadrantes/bounds?** | **No hay cuadrantes** en Planificación. Mapa = distrito GeoJSON + pins por lat/lng. |
| **Cambio mínimo con más impacto** | Paginar/filtrar agregables **en SQL**; **no re-ejecutar** load-all por cada página; **batch eligibility**; frontend **dejar de refetch M4 completo** al mutar pool. |

---

## 1. Mapa de archivos — Frontend

### 1.1 Pantalla y flujo

```
index.tsx (RutasTrabajo)
  flowStep 1 → PlanificacionView
  flowStep 2 → RutasPlanificacionView (Asignación — NO TOCAR)
  flowStep 3 → RutasMapaOperativoView (Mapa final — NO TOCAR)
  useRutaPoolDiaBackend → poolControl
  useRutasTrabajoSession → ruta, grupos, items
```

| Archivo | Rol |
|---------|-----|
| `Frontend/src/Containers/RutasTrabajo/index.tsx` | Orquestador, pool, sync post-quitar-grupo |
| `Frontend/src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx` | Layout 3 columnas + mapa popup/flyTo |
| `Frontend/src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts` | **Hub M1–M4** (estado, effects, derivados) |
| `Frontend/src/Containers/RutasTrabajo/hooks/useRutaPoolDiaBackend.ts` | Pool GET/POST/DELETE |
| `Frontend/src/Containers/RutasTrabajo/Components/RutasTrabajoFlowStepper.tsx` | Steps 1/2/3 |

### 1.2 Mapa / geocodificación (Planificación)

| Archivo | Rol |
|---------|-----|
| `planificacion/PlanificacionMapaDistritos.tsx` | Leaflet + GeoJSON distritos (M2) |
| `planificacion/PlanificacionMapaPendientesLayer.tsx` | Marcadores M4 |
| `planificacion/PlanificacionMapaDistritoLabelsLayer.tsx` | Labels cantidad/distrito |
| `planificacion/utils/iniciadorCoords.ts` | `parseIniciadorLatLng` (lat/lng del DTO) |
| `planificacion/utils/planificacionMapaPins.ts` | Iconos por prioridad (verde/amarillo/rojo) |
| `planificacion/utils/mergePlanificacionDistritosGeo.ts` | Merge GeoJSON + catálogo DB |

**Marcadores:** `ctrl.pendientesParaMapa` → pins con geocode → **no incluye pool/grupo como capa separada**.

**Cuadrantes/bounds:** no existen. Distrito = polígono estático; `flyTo` zoom 16 al pin.

**Refetch mapa (M4):** `useEffect` deps `[distritoActivoId, rutaId, poolIniciadorKey]`.

### 1.3 Candidatos M4

| Item | Detalle |
|------|---------|
| API | `GET /rutas-trabajo/:id/planificacion/pendientes-contexto` |
| Cliente | `planificacion/api/planificacionApi.ts` → `getPlanificacionPendientesContexto` |
| Query enviada | `distrito_id`, `orden=prioridad`, `page`, `per_page=500`, `fields=minimal` |
| Filtros backend | solo distrito + agregables (6I) |
| Filtros frontend | pool (`sinPool`), geocode, rubro, q domicilio, KPI card — **en memoria** |
| Paginación lista | **Cliente** (25/página sobre dataset ya cargado) |
| Carga mapa | **Loop** hasta `meta.total` (máx 40 páginas × 500) |

### 1.4 Urgentes globales M3

| Item | Detalle |
|------|---------|
| Componente | `planificacion/UrgentesPanel.tsx` |
| API | `GET /rutas-trabajo/:id/planificacion/urgentes` |
| Carga | Montaje + **cada cambio de pool** (`poolIniciadorKey`) |
| Paginación | **Server** (25/página) |
| Filtros backend | tipo urgente, domicilio, agregables (6J) |
| Filtros frontend | ocultar ids en pool local |

### 1.5 Pool y grupos

| Item | Detalle |
|------|---------|
| Hook | `hooks/useRutaPoolDiaBackend.ts` |
| API | `GET/POST/DELETE /ruta-pool-dia` con `ruta_trabajo_id` (6H) |
| UI Planificación | `planificacion/PoolDelDiaPanel.tsx` |
| Grupos | Solo paso 2 (`RutasPlanificacionView`) — no en mapa Planificación |
| Pines pool en mapa | **No hay capa roja**; popup muestra "En pool" / botón deshabilitado |

### 1.6 Performance frontend (red flags)

1. **M4 bulk loop** — secuencial, hasta 40 requests; **cada request re-procesa todo el universo en backend**.
2. **`poolIniciadorKey`** — refetch M4 + M3 en cada add/remove pool (aunque pool ya se filtra client-side).
3. **N marcadores Leaflet** — uno por pin; `planificacionPendientePinIcon` recreado sin memo.
4. **GeoJSON remount** — `mapKey` cambia al seleccionar distrito.
5. **Lista M4 excluye sin geocode** — mismo dataset que mapa, usuarios pueden ver menos filas que pins esperados.

---

## 2. Mapa de endpoints — Backend

### 2.1 M4 — `pendientes-contexto`

```
routes/planificacion.py
  → planificacion_service.get_planificacion_pendientes_contexto
  → iniciadores_pendientes_service.get_iniciadores_pendientes_para_ruta
       solo_agregables_ruta=True
       distrito=<obligatorio>
```

**Query base:** `planificable_iniciadores_base_query()` — PENDIENTE, no deleted, sin ítem activo en ruta BORRADOR, **eager load pesado** (domicilio, relevamiento, oficio, notificación…).

**Pipeline M4 (distrito):**
1. `query.order_by(...).all()` → **todos** los candidatos SQL
2. Por cada fila: `resolve_domicilio_efectivo_para_iniciador` + `get(Domicilio)` — **N+1**
3. Filtro distrito en Python (domicilio **efectivo**, no FK cruda)
4. `filtrar_iniciadores_agregables_a_ruta` — **N+1 elegibilidad** por iniciador
5. Paginación en memoria + `db.session.commit()` en GET (side effects domicilio)

### 2.2 Urgentes M3

```
routes/planificacion.py
  → planificacion_service.get_planificacion_urgentes
       planificable base + prioridad>=3 + tipo!=RELEVAMIENTO
       .all() → filtrar_iniciadores_agregables_a_ruta → slice page
```

Distrito en M3: filtro SQL `Domicilio.distrito_id` (≠ M4 que usa efectivo).

### 2.3 Pool

| Método | Ruta | Service |
|--------|------|---------|
| GET | `/ruta-pool-dia` | `list_ruta_pool_dia` — paginación SQL OK |
| POST | `/ruta-pool-dia` | `create_ruta_pool_dia_entry` / `ensure_pool_en_pool_para_ruta` |
| DELETE | `/ruta-pool-dia/:id` | `descartar_ruta_pool_dia_entry` |
| POST | `/ruta-pool-dia/:id/liberar` | `liberar_ruta_pool_dia_entry` |

### 2.4 Grupos / ítems

| Acción | Service |
|--------|---------|
| Agregar desde pool | `agregar_desde_pool_a_ruta` |
| Quitar ítem | `soft_delete_ruta_item` → `devolver_iniciador_al_pool_ruta` |
| Eliminar grupo | `soft_delete_grupo` |
| Asignar | `assign_iniciadores_to_grupo` |

### 2.5 Helpers elegibilidad (6F–6J)

Archivo: `services/ruta_pool_dia_eligibility_service.py`

| Función | Uso |
|---------|-----|
| `es_iniciador_agregable_a_ruta` | Decisión unitaria mapa/urgentes |
| `filtrar_iniciadores_agregables_a_ruta` | Lista M3/M4 |
| `pool_row_bloquea_planificacion` | Pool EN_POOL / ASIGNADO |
| `iniciador_en_ruta_borrador_activa` | Ítem en grupo borrador |
| `ensure_pool_en_pool_para_ruta` | Idempotencia pool (6I) |
| `build_estado_operativo_pool_por_iniciador` | Badges operativos (presenter) |

---

## 3. Diagrama de flujo actual

```
[Usuario abre Ruta BORRADOR / Planificación]
        │
        ├─► M2 carga-distritos (mount)
        ├─► M3 urgentes page=1 (mount) ──────────────┐
        └─► Pool GET EN_POOL (mount)                 │
                │                                     │
[Usuario selecciona distrito]                        │
        │                                             │
        └─► M4 loop page=1..N (500 c/u) ◄────────────┤
                │   backend: .all() → distrito Python │
                │            → agregables N+1         │
                └─► pendientesMapaRaw (merge)         │
                        │                             │
                        ├─► sinPool (client)          │
                        ├─► filasConPinMapa           │
                        ├─► filtros panel + KPI card  │
                        └─► Leaflet markers           │
                                                        │
[Usuario agrega al pool] ◄──────────────────────────────┘
        │
        ├─► POST pool
        ├─► refreshPool
        ├─► poolIniciadorKey cambia
        ├─► RE-FETCH M3 urgentes (page 1)
        └─► RE-FETCH M4 loop completo
```

**Observación clave:** el pool ya se oculta en cliente (`sinPool`), pero **igual se re-descarga todo M4/M3** desde backend.

---

## 4. Tabla de tiempos medidos

Medición con `PLANIFICACION_DEBUG=1` y script `Backend/scripts/benchmark_oper_ruta_7a.py`  
Entorno: BD local de test, **ruta_id=6764**, **distrito_id=1**, fecha ruta 2026-09-30.

| Tag | total_ms | rows_base | rows_final | descartados | Notas |
|-----|----------|-----------|------------|-------------|-------|
| **OPER_RUTA_7A_URGENTES** | **6.453** | 1.869 | 1.556 | 313 (agregables) | Solo page 1 (25 ítems respuesta) |
| **OPER_RUTA_7A_M4** | **15.883** | 4.196 | 92 | 39 agregables (131→92 tras distrito) | sql_fetch_ms=622; resto = domicilio efectivo + elegibilidad |

**Estimación frontend (peor caso):**

| Escenario | Cálculo | Tiempo backend aprox. |
|-----------|---------|------------------------|
| 1 distrito, total ≤ 500 | 1 × M4 | ~16 s |
| 1 distrito, total = 2.500 | 5 × M4 (cada una re-scan 4k+) | **~60–80 s** |
| Montaje + urgentes + M4 | 6.5 s + 16 s | **~22 s** |
| + refetch por pool | +22 s | percepción "minuto" |

**Payload:** M4 `fields=minimal` ~18 campos × N pins; 500 pins ≈ cientos de KB–1 MB JSON por página.

**Render FE (estimado):** 92 markers ≈ instantáneo; 1.000+ markers Leaflet puede sumar segundos en DOM.

---

## 5. Causa probable de lentitud (~1 min)

1. **Backend load-all-then-filter** en M3 y M4 (no escala con volumen de cola PENDIENTE).
2. **N+1** en `filtrar_iniciadores_agregables_a_ruta` (~3–5 queries × miles de filas).
3. **N+1 domicilio efectivo** en M4 por cada candidato antes de filtrar distrito.
4. **Frontend M4 multi-página** — cada página repite el pipeline completo.
5. **Refetch M4+M3 on pool change** — innecesario si backend ya filtra agregables y cliente ya hace `sinPool`.
6. **Eager load graph** en query base aunque `fields=minimal`.

---

## 6. Propuesta visual (solo relevamiento — no implementado)

| Estado | Pin actual | Propuesta 7E |
|--------|------------|--------------|
| Candidato libre agregable | Verde/amarillo/rojo por prioridad | Mantener |
| En pool EN_POOL | Mismo pin (popup "En pool") | **Círculo rojo sólido** |
| En grupo / ítem borrador | No visible en mapa Planificación | **Círculo rojo** (misma coords) |
| Urgente libre | Igual que candidato | Opcional borde/icono |
| Línea roja ruta | No existe | Leaflet `Polyline` — viable en capa aparte (futuro) |

**Viabilidad:** Leaflet ya usado; agregar `PlanificacionMapaPoolLayer.tsx` con coords de `poolControl` + ítems borrador de `ruta` **sin tocar Mapa final**. Estilo: `L.divIcon` circular rojo (distinto de `planificacionPendientePinIcon`).

---

## 7. Propuesta de PRs chicos (recomendado orden)

| PR | Objetivo | Riesgo |
|----|----------|--------|
| **OPER-RUTA.7B** | Backend: candidatos paginados/filtrados server-side; batch eligibility; SQL distrito donde sea posible; eliminar `.all()` + re-scan por página | Medio |
| **OPER-RUTA.7C** | Frontend: panel/lista tipo My Maps sobre endpoint optimizado; reducir M4 loop; paginación real | Medio |
| **OPER-RUTA.7D** | Urgentes como filtro/vista del mismo endpoint (o query param `urgentes=1`) — una sola query base | Bajo–Medio |
| **OPER-RUTA.7E** | Pines rojos pool/grupo/items usados en mapa Planificación | Bajo |
| **OPER-RUTA.7F** | Limpieza: quitar refetch M4 al mutar pool (o invalidación selectiva); memo icons; quitar commit en GET | Bajo |

**Intuición confirmada:** **primero backend/payload (7B), después UI (7C–7E)**.

---

## 8. Qué conservar vs reemplazar

| Conservar | Reemplazar / refactorizar |
|-----------|---------------------------|
| Flujo 3 pasos + pool por ruta (6H) | Load-all M3/M4 |
| Elegibilidad 6F–6J (reglas) | Implementación N+1 unitaria |
| Mapa distritos M2 (GeoJSON) | Refetch M4 completo on pool |
| Filtros panel en cliente (rubro/q) | Multi-página que re-ejecuta backend |
| `fields=minimal` para pins | Eager load completo en query base |
| Pool panel + `useRutaPoolDiaBackend` | — |

---

## 9. Riesgos al modificar

- **Distrito efectivo (M4) vs distrito FK (M3/M1)** — unificar mal rompe territorialidad PR5.
- **`db.session.commit()` en GET M4** — side effects domicilio; mover con cuidado.
- **KPI cards derivadas de pins** — cambiar dataset afecta métricas visibles.
- **Tests 6I/6J** — cualquier optimización SQL debe preservar elegibilidad.
- **Cap 20k pins** — distritos densos pueden truncar mapa.

---

## 10. Tests a cubrir antes de modificar

- `test_oper_ruta_6i_mapa_pool_quitar.py`
- `test_oper_ruta_6j_urgentes_globales.py`
- `test_oper_ruta_6h_pool_ruta_filtro.py`
- `test_oper_ruta_6f_replanificacion.py`
- Frontend: `operRuta6i.test.ts`, `operRuta6j.test.ts`, `planificacionSelectors.test.ts`

---

## 11. Instrumentación temporal (gated)

| Archivo | Activación |
|---------|------------|
| `Backend/app/domains/rutas_trabajo/utils/planificacion_debug.py` | `PLANIFICACION_DEBUG=1` |
| Logs en `iniciadores_pendientes_service.py`, `planificacion_service.py` | `[OPER_RUTA_7A_M4]`, `[OPER_RUTA_7A_URGENTES]` |
| `Backend/scripts/benchmark_oper_ruta_7a.py` | Benchmark local |

**Remover o dejar gated antes de merge a prod** (default off).

---

## 12. Respuestas F (checklist)

| # | Respuesta |
|---|-----------|
| 1 | **M4 backend** tarda más (~16 s/distrito en test; hasta ~60 s+ con multi-página FE). |
| 2 | **Backend** (~80%) + **frontend** amplifica (multi-request, refetch pool). |
| 3 | ~4.200 planificables SQL; ~92 agregables en distrito 1. |
| 4 | **Sí**, backend trae todo y filtra en Python. |
| 5 | **Sí**, urgentes pueden ser filtro/vista del mismo universo optimizado. |
| 6 | **No hay cuadrantes**; solo distrito + pins lat/lng. |
| 7 | Conservar: steps, pool/ruta, reglas 6F–6J, mapa distritos, Leaflet. |
| 8 | Reemplazar: load-all, N+1, M4 loop, refetch on pool. |
| 9 | Pines rojos = **nueva capa Leaflet** en Planificación (7E), no tocar mapa final. |
| 10 | Mínimo impacto: batch eligibility + paginar SQL + stop refetch M4 on pool. |
| 11 | Riesgo medio en 7B (distrito efectivo + agregables); bajo en 7E. |
| 12 | Tests 6F–6J + selectors FE antes de tocar. |

---

## 13. Qué NO conviene tocar (en próximos PRs)

- `RutasMapaOperativoView` / Mapa final (paso 3)
- `RutasPlanificacionView` asignación cerrada (paso 2) salvo refresh pool ya existente
- `ruta_publicar_service` / PR11
- Geocode pipeline
- Indicadores, exports, CRUDs periféricos

---

*Generado en OPER-RUTA.7A. Instrumentación de medición incluida; desactivar con `PLANIFICACION_DEBUG` unset.*
