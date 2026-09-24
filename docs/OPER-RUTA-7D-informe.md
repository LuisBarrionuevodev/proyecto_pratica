# OPER-RUTA.7D — Optimizar Urgentes globales (M3)

> **Alcance:** backend M3 optimizado; sin cambios visuales frontend.  
> **Fecha:** 2026-08-20

---

## Endpoint M3

| Item | Detalle |
|------|---------|
| **Ruta** | `GET /rutas-trabajo/:ruta_id/planificacion/urgentes` |
| **Service** | `get_planificacion_urgentes` en `planificacion_service.py` |
| **Presenter** | `iniciador_pendiente_present(row, fields="full")` |

### Parámetros

`page`, `per_page` (max 100), `distrito_id`, `tipo_urgente`, `q`, `numero_oficio`, `numero_comprobacion`, `q_identificador`, `q_domicilio`, `rubro_id`

### Contrato response (sin cambios)

```json
{
  "items": [...],
  "meta": { "total": 1620, "page": 1, "per_page": 25 }
}
```

### Regla “urgente” (semántica mantenida)

- `estado_iniciador == PENDIENTE`, no deleted
- `planificable_iniciadores_base_query` (sin ítem en ruta BORRADOR)
- `tipo_iniciador != RELEVAMIENTO`
- `prioridad >= 3`
- Agregables 6I/6J: sin pool EN_POOL / ASIGNADO activo; sin ítem abierto en ruta no borrador
- `distrito_id`: filtro por **domicilio FK** del iniciador (igual M1 métrica `alta`, no domicilio efectivo M4)

---

## Causa de lentitud (antes)

Patrón idéntico al viejo M4:

```
planificable_base + urgentes filters → .all() (~1.869)
→ filtrar_iniciadores_agregables_a_ruta (N+1) → ~1.556
→ slice paginación en memoria
```

---

## Query nueva (7D)

```
planificable_iniciadores_base_query()
+ prioridad >= 3, tipo != RELEVAMIENTO
+ apply_urgentes_filtros (SQL)
+ apply_sql_exclusion_pool_y_ruta_activa (NOT EXISTS — reutilizado de 7B)
+ query.count()
+ order_by + offset/limit
+ _enriquecer_domicilio_efectivo_pagina (solo página)
```

**Sin** `.all()` masivo. **Sin** `filtrar_iniciadores_agregables_a_ruta` en Python.

---

## Helpers reutilizados de 7B / 6I / 6J

| Helper | Uso M3 |
|--------|--------|
| `apply_sql_exclusion_pool_y_ruta_activa` | Pool EN_POOL, ASIGNADO bloqueante, ítems ruta PUBLICADA/EN_CURSO |
| `planificable_iniciadores_base_query` | Excluye ítems BORRADOR |
| `_enriquecer_domicilio_efectivo_pagina` | Backfill/sync solo en página |
| `apply_urgentes_filtros` | Filtros texto/tipo/rubro (existente) |

---

## Performance

| Métrica | Antes (7A) | Después (7D) |
|---------|------------|--------------|
| M3 page 1 (per_page=25) | **~6.5 s** | **~0.14 s** |
| rows_base `.all()` | ~1.869 | 0 |
| total filtrado | ~1.556 | 1.620 (SQL count) |
| items page | 25 | 25 |

Log (`PLANIFICACION_DEBUG=1`):

```txt
[OPER_RUTA_7D_URGENTES] ruta=6948 page=1 per_page=25 count_ms=23 total=1620 rows_page=25 sql_ms=38 enrich_ms=71 total_ms=135
```

---

## Archivos tocados

| Archivo | Cambio |
|---------|--------|
| `services/planificacion_service.py` | M3 optimizado SQL |
| `utils/planificacion_debug.py` | `[OPER_RUTA_7D_URGENTES]` |
| `tests/test_oper_ruta_7d_urgentes.py` | **Nuevo** — 10 tests |

M4 7B no modificado (solo reutilización de `planificacion_m4_sql.py`).

---

## Tests ejecutados

- `test_oper_ruta_7d_urgentes.py` — 10 passed
- `test_oper_ruta_6j_urgentes_globales.py` — 9 passed (regresión)
- `test_oper_ruta_7b_m4_paginado.py` — 9 passed

Frontend: no tocado.

---

## Confirmación de alcance

No se tocó: UI My Maps, pines rojos, publicar, Completar Trabajo, PR11/PR12, geocode, exports, indicadores, CRUDs, M4 implementación 7B.

---

## Siguiente paso

Base rápida completa (M4 ~0.5s, M3 ~0.14s, sin refetch pool 7F.1) → **7C/7E** reacondicionamiento visual.
