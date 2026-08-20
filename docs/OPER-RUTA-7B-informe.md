# OPER-RUTA.7B — Backend M4 paginado/filtrado server-side

> **Alcance:** optimización backend M4 sin cambios visuales frontend.  
> **Fecha:** 2026-08-20

---

## Resumen

| Métrica | Antes (7A) | Después (7B) |
|---------|------------|--------------|
| M4 page 1 (ruta ~6849, distrito 1, per_page=500) | **~15.9 s** | **~0.48 s** |
| rows_base procesados | ~4.196 (`.all()`) | 0 masivo |
| items page | 92 | 92 |
| total filtrado | 92 | 92 |
| count_ms / sql_ms / enrich_ms | N/A | 37 / 245 / 193 ms |

**Clave:** la página 2 ya no re-ejecuta el pipeline sobre 4k+ iniciadores; cada página usa `COUNT` + `LIMIT/OFFSET` sobre query filtrada en SQL.

---

## Archivos tocados

| Archivo | Cambio |
|---------|--------|
| `utils/planificacion_m4_sql.py` | **Nuevo** — NOT EXISTS pool/ruta + distrito domicilio efectivo en SQL |
| `services/iniciadores_pendientes_service.py` | Path M4 optimizado `_get_iniciadores_pendientes_m4_optimizado` |
| `services/ruta_pool_dia_eligibility_service.py` | `filtrar_iniciadores_agregables_a_ruta_batch` (alias documentado) |
| `utils/planificacion_debug.py` | Logs `[OPER_RUTA_7B_M4]` gated |
| `tests/test_oper_ruta_7b_m4_paginado.py` | **Nuevo** — 9 tests M4 |

**No tocado:** frontend, publicar, Completar Trabajo, PR11/PR12, geocode, M3 urgentes (salvo helpers SQL reutilizables).

---

## Query anterior vs nueva

### Anterior (7A)

```
planificable_base_query().all()           → ~4.196 filas + eager load
por cada fila: resolve_domicilio_efectivo → N+1
filtro distrito en Python
filtrar_iniciadores_agregables_a_ruta     → N+1 elegibilidad
slice [page*per_page] en memoria
```

### Nueva (7B) — path M4 (`solo_agregables_ruta` + `distrito` + orden planificación)

```
planificable_base_query()
+ filtros opcionales SQL (tipo, q, prioridad, calle, turno)
+ apply_sql_exclusion_pool_y_ruta_activa()     → NOT EXISTS
+ apply_joins_y_filtro_distrito_efectivo()     → domicilio efectivo PR5 en SQL
query.count()                                  → total agregable/distrito
query.order_by(...).offset().limit().all()   → solo página
enriquecer domicilio efectivo solo en página → backfill/sync PR2
```

---

## Cómo se eliminó `.all()` masivo

- M4 (`get_planificacion_pendientes_contexto`) entra al path optimizado cuando `solo_agregables_ruta=True`, `distrito` informado y `orden_planificacion=True`.
- Paginación real con `offset/limit` tras `count()` sobre query ya filtrada.
- Path legacy (sin distrito o sin agregables) conserva comportamiento anterior o usa SQL parcial para `solo_agregables` sin distrito.

---

## Domicilio efectivo sin N+1 en el scan

- **Filtro distrito:** expresión SQL equivalente a `resolve_domicilio_efectivo_para_iniciador` (joins relevamiento/denuncia/actuación/oficio/comprobación/notificación + `CASE` de alineación).
- **Enriquecimiento post-página:** `resolve_domicilio_efectivo_para_iniciador` solo sobre `rows_page` (típico ≤500), no sobre el universo completo.

---

## Elegibilidad sin N+1

- Exclusiones 6I/6J en SQL vía `apply_sql_exclusion_pool_y_ruta_activa`:
  - `NOT EXISTS` pool `EN_POOL`
  - `NOT EXISTS` pool `ASIGNADO_A_RUTA` con ítem abierto
  - `NOT EXISTS` ítem abierto en ruta PUBLICADA/EN_CURSO/CERRADA/CANCELADA
- Exclusión ítems BORRADOR: sigue en `planificable_iniciadores_base_query` (compatible con comportamiento previo).

---

## Filtros server-side

| Filtro | SQL |
|--------|-----|
| `distrito_id` | domicilio efectivo |
| `tipo` | `IniciadorRuta.tipo_iniciador` |
| `prioridad` / `prioridad_categoria` | prioridad |
| `q` | calle/número/observaciones (domicilio FK iniciador) |
| `calle_catalogo_id` | domicilio FK |
| `turno_sugerido` | iniciador |
| agregables | NOT EXISTS pool/ruta |

`rubro_id` M4: sigue en cliente (STAB-10d); no se agregó en este PR.

---

## Contrato de respuesta

Sin cambios:

```json
{
  "items": [...],
  "meta": {
    "total": 92,
    "page": 1,
    "per_page": 500,
    "fields": "minimal"
  }
}
```

---

## Instrumentación

`PLANIFICACION_DEBUG=1`:

```txt
[OPER_RUTA_7B_M4] ruta=6849 distrito=1 page=1 per_page=500 count_ms=37 total=92 rows_page=92 sql_ms=245 enrich_ms=193 total_ms=484
```

---

## Tests ejecutados

- `tests/test_oper_ruta_7b_m4_paginado.py` — 9 passed
- `tests/test_oper_ruta_6i_mapa_pool_quitar.py` — passed (regresión)
- `tests/test_oper_ruta_6j_urgentes_globales.py` — passed
- `tests/test_hotfix_reencolado_planificacion.py` — passed
- `tests -k "oper_ruta_7b or pendientes_contexto"` — passed
- `tests -k "replanificacion or oper_ruta_6f"` — passed
- `tests -k "ruta_pool"` — 1 fallo preexistente `test_listado_filtra_por_fecha` (no relacionado con 7B)

---

## Confirmación de alcance

- No se implementó UI My Maps, pines rojos, urgentes como filtro, ni limpieza de loop frontend (7C–7F).
- No se tocó publicar, Completar Trabajo, PR11/PR12, geocode, indicadores, exports, CRUDs.

---

## Siguiente paso (7C)

Frontend puede reducir loop M4: con `total=92` y `per_page=500`, **una sola request** cubre el mapa. El refetch al mutar pool (7F) sigue pendiente.
